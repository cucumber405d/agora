from pydantic_ai.exceptions import UnexpectedModelBehavior

from ibikus.appa.agora.context import Context
from ibikus.appa.agora.reflection.graph import (
    build_graph,
    is_approved,
    route,
    select_final,
    to_result,
)
from ibikus.appa.agora.reflection.state import initial_state

from .fakes import Recorder, c, cfg, collect, make_agents


async def test_approved_on_first_iteration() -> None:
    conf = cfg(max_iterations=3)
    graph = build_graph(make_agents(["AA"], [c(9, approved=True)]), conf)
    ev, st = await collect(graph, "Q")
    r = to_result(st, conf)
    assert (r.status, r.final, r.iterations, r.best_score) == ("approved", "AA", 1, 9)
    assert [e.kind for e in ev if e.kind != "llm_exchange"] == [
        "iteration_started",
        "draft_chunk",
        "draft_chunk",
        "draft_done",
        "critique_done",
    ]
    assert ev[0].max_iterations == 3


async def test_high_score_without_approval_continues() -> None:
    conf = cfg(approve_threshold=8)
    _, st = await collect(
        build_graph(make_agents(["A", "B"], [c(9), c(9, approved=True)]), conf), "Q"
    )
    r = to_result(st, conf)
    assert (r.status, r.iterations, r.final) == ("approved", 2, "B")


async def test_approved_below_threshold_continues() -> None:
    """approve_threshold is a hard floor: the critic's approval alone is not enough."""
    conf = cfg(approve_threshold=10, max_iterations=3)
    agents = make_agents(["A", "B", "C"], [c(9, approved=True)] * 3)
    _, st = await collect(build_graph(agents, conf), "Q")
    r = to_result(st, conf)
    assert (r.status, r.iterations) == ("max_iterations", 3)


async def test_approved_at_threshold_stops() -> None:
    conf = cfg(approve_threshold=10)
    _, st = await collect(build_graph(make_agents(["A"], [c(10, approved=True)]), conf), "Q")
    assert (to_result(st, conf).status, st["iteration"]) == ("approved", 1)


async def test_improves_until_threshold() -> None:
    conf = cfg()
    _, st = await collect(
        build_graph(make_agents(["A", "B"], [c(5), c(9, approved=True)]), conf), "Q"
    )
    r = to_result(st, conf)
    assert (r.status, r.iterations, r.final) == ("approved", 2, "B")
    assert [h.critique.score for h in r.history] == [5, 9]


async def test_max_iterations_picks_best_draft() -> None:
    conf = cfg(max_iterations=3)
    _, st = await collect(build_graph(make_agents(["A", "B", "C"], [c(6), c(7), c(4)]), conf), "Q")
    r = to_result(st, conf)
    assert (r.status, r.final, r.best_score, r.iterations) == ("max_iterations", "B", 7, 3)


async def test_tie_prefers_later_draft() -> None:
    conf = cfg(max_iterations=2)
    _, st = await collect(build_graph(make_agents(["A", "B"], [c(6), c(6)]), conf), "Q")
    assert to_result(st, conf).final == "B"


async def test_second_generation_sees_critique() -> None:
    rec = Recorder()
    agents = make_agents(["A", "B"], [c(3, issues=["missing example"]), c(9)], recorder=rec)
    await collect(build_graph(agents, cfg()), "Q")
    assert "## Critique" not in rec.generator_inputs[0]
    assert "## Critique" in rec.generator_inputs[1]
    assert "missing example" in rec.generator_inputs[1]


async def test_critic_failure_later_keeps_run_with_latest_draft() -> None:
    conf = cfg(max_iterations=3)
    agents = make_agents(["A", "B"], [c(5), UnexpectedModelBehavior("bad json")])
    ev, st = await collect(build_graph(agents, conf), "Q")
    r = to_result(st, conf)
    assert (r.status, r.final, r.iterations, r.best_score) == ("critic_failed", "B", 2, 5)
    assert [h.iteration for h in r.history] == [1]  # only graded iterations
    failed = [e for e in ev if e.kind == "critique_failed"]
    assert len(failed) == 1 and failed[0].iteration == 2
    assert "bad json" in failed[0].message


async def test_critic_failure_first_iteration() -> None:
    conf = cfg()
    _, st = await collect(build_graph(make_agents(["A"], ["**Score:** 8"]), conf), "Q")
    r = to_result(st, conf)
    assert (r.status, r.final, r.iterations, r.best_score, r.history) == (
        "critic_failed",
        "A",
        1,
        0,
        [],
    )


def test_select_final_pure() -> None:
    assert select_final(["a", "b", "c"], [c(5), c(8), c(8)], approved=False) == ("c", 2)
    assert select_final(["a", "b"], [c(9), c(2)], approved=True) == ("b", 1)


def test_is_approved() -> None:
    assert not is_approved(c(6, approved=True), 8)  # below the floor
    assert not is_approved(c(8), 8)  # critic did not approve
    assert is_approved(c(8, approved=True), 8)
    assert not is_approved(c(7), 8)


def test_route() -> None:
    st = initial_state("Q", Context.empty())
    st["iteration"], st["drafts"], st["critiques"] = 1, ["a"], [c(2)]
    assert route(st, cfg(max_iterations=2)) == "generate"
    st["iteration"] = 2
    assert route(st, cfg(max_iterations=2)) == "finalize"


async def test_max_allowed_iterations_fit_recursion_limit() -> None:
    conf = cfg(max_iterations=10)
    _, st = await collect(build_graph(make_agents(["A"], [c(1)]), conf), "Q")
    assert to_result(st, conf).iterations == 10


def _truncating_generator():  # type: ignore[no-untyped-def]
    """An Ollama model whose stream stops with finish_reason=length (context exhausted)."""
    import json

    import httpx
    from openai import AsyncOpenAI
    from pydantic_ai.models.ollama import OllamaModel
    from pydantic_ai.providers.ollama import OllamaProvider

    from ibikus.appa.agora.agents.generator import build_generator

    def chunk(delta: dict[str, str], finish: str | None) -> str:
        payload = {
            "id": "x",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "m",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        return f"data: {json.dumps(payload)}\n\n"

    def sse(req: httpx.Request) -> httpx.Response:
        body = (
            chunk({"role": "assistant", "content": "Cut off te"}, None)
            + chunk({}, "length")
            + "data: [DONE]\n\n"
        )
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    client = AsyncOpenAI(
        base_url="http://x/v1",
        api_key="k",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(sse)),
    )
    return build_generator(OllamaModel("m", provider=OllamaProvider(openai_client=client)), {}, "g")


async def test_truncated_draft_is_flagged_and_told_to_critic() -> None:
    from dataclasses import replace

    from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    from ibikus.appa.agora.agents.critic import build_critic

    critic_inputs: list[str] = []

    def crit(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        critic_inputs.append(str(messages[-1]))
        return ModelResponse(parts=[TextPart(c(9, approved=True).model_dump_json())])

    agents = replace(
        make_agents(["unused"], [c(9, approved=True)]),
        generator=_truncating_generator(),
        critic=build_critic(FunctionModel(crit), {}, "c"),
    )
    ev, _ = await collect(build_graph(agents, cfg()), "Q")
    done = [e for e in ev if e.kind == "draft_done"]
    assert done[0].truncated is True
    assert done[0].text == "Cut off te"
    assert "was cut off" in critic_inputs[0]


async def test_graph_tells_both_agents_the_prompt_language() -> None:
    rec = Recorder()
    agents = make_agents(["A"], [c(9, approved=True)], recorder=rec)
    await collect(build_graph(agents, cfg()), "расскажи сказку")
    assert "Answer in Russian." in rec.generator_inputs[0]


async def test_configured_language_overrides_detection() -> None:
    rec = Recorder()
    agents = make_agents(["A"], [c(9, approved=True)], recorder=rec)
    await collect(build_graph(agents, cfg(language="German")), "расскажи сказку")
    assert "Answer in German." in rec.generator_inputs[0]


async def test_result_names_selected_iteration() -> None:
    conf = cfg(max_iterations=3)
    _, st = await collect(build_graph(make_agents(["A", "B", "C"], [c(6), c(7), c(4)]), conf), "Q")
    r = to_result(st, conf)
    assert (r.selected_iteration, r.selected_score, r.final) == (2, 7, "B")


async def test_result_approved_selects_last() -> None:
    conf = cfg()
    agents = make_agents(["A", "B"], [c(5), c(9, approved=True)])
    _, st = await collect(build_graph(agents, conf), "Q")
    r = to_result(st, conf)
    assert (r.selected_iteration, r.selected_score) == (2, 9)


async def test_result_critic_failed_selection_is_ungraded() -> None:
    conf = cfg()
    agents = make_agents(["A", "B"], [c(5), UnexpectedModelBehavior("x")])
    _, st = await collect(build_graph(agents, conf), "Q")
    r = to_result(st, conf)
    assert (r.selected_iteration, r.selected_score) == (2, None)


async def test_llm_exchanges_are_logged_in_order() -> None:
    ev, _ = await collect(build_graph(make_agents(["AB"], [c(9, approved=True)]), cfg()), "Q")
    log = [(e.role, e.direction) for e in ev if e.kind == "llm_exchange"]
    assert log == [
        ("generator", "request"),
        ("generator", "response"),
        ("critic", "request"),
        ("critic", "response"),
    ]
    request = next(e for e in ev if e.kind == "llm_exchange" and e.direction == "request")
    assert "## Request\nQ" in request.text
    assert request.tokens is not None and request.tokens > 0
    response = next(
        e
        for e in ev
        if e.kind == "llm_exchange" and e.role == "generator" and e.direction == "response"
    )
    assert response.text == "AB"
    assert response.seconds is not None


async def test_llm_log_shows_critic_retry() -> None:
    from ibikus.appa.agora.reflection.events import LlmExchange

    agents = make_agents(["A"], [c(9, approved=True)])
    ev, _ = await collect(build_graph(agents, cfg()), "расскажи")  # English feedback -> 1 retry
    crit = [e.direction for e in ev if isinstance(e, LlmExchange) and e.role == "critic"]
    assert crit == ["request", "response", "retry", "response"]
    retry = next(e for e in ev if isinstance(e, LlmExchange) and e.direction == "retry")
    assert "Russian" in retry.text


async def test_llm_log_marks_critic_failure_as_error() -> None:
    from ibikus.appa.agora.reflection.events import LlmExchange

    agents = make_agents(["A"], [UnexpectedModelBehavior("bad json")])
    ev, _ = await collect(build_graph(agents, cfg()), "Q")
    errors = [e for e in ev if isinstance(e, LlmExchange) and e.direction == "error"]
    assert len(errors) == 1 and errors[0].role == "critic" and "bad json" in errors[0].text


async def test_llm_log_marks_generator_failure_as_error() -> None:
    import pytest
    from pydantic_ai.exceptions import ModelConnectionError

    from ibikus.appa.agora.reflection.events import LlmExchange

    events: list[object] = []
    agents = make_agents([ModelConnectionError("m", "refused")], [c(9)])
    graph = build_graph(agents, cfg())
    from ibikus.appa.agora.context import Context
    from ibikus.appa.agora.reflection.state import initial_state

    with pytest.raises(ModelConnectionError):
        async for mode, payload in graph.astream(
            initial_state("Q", Context.empty()), stream_mode=["custom", "values"]
        ):
            if mode == "custom":
                events.append(payload)
    errors = [e for e in events if isinstance(e, LlmExchange) and e.direction == "error"]
    assert len(errors) == 1 and "refused" in errors[0].text


async def test_request_previews_describe_the_step() -> None:
    from ibikus.appa.agora.reflection.events import LlmExchange

    agents = make_agents(["AB", "CD"], [c(5, issues=["x", "y"]), c(9, approved=True)])
    ev, _ = await collect(build_graph(agents, cfg()), "a tale")  # English: no language retry
    previews = [e.preview for e in ev if isinstance(e, LlmExchange) and e.direction == "request"]
    assert previews[0] == "It1: «a tale»"
    assert previews[1] == "It1: review draft 2 chars"
    assert previews[2] == "It2: revise after score 5, 2 issues"
