import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior

from ibikus.appa.agora.context import Context
from ibikus.appa.agora.reflection.graph import (
    CriticInvalidError,
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
    assert [e.kind for e in ev] == [
        "iteration_started",
        "draft_chunk",
        "draft_chunk",
        "draft_done",
        "critique_done",
    ]
    assert ev[0].max_iterations == 3


async def test_threshold_counts_as_approval() -> None:
    conf = cfg(approve_threshold=8)
    _, st = await collect(build_graph(make_agents(["A"], [c(8)]), conf), "Q")
    r = to_result(st, conf)
    assert (r.status, r.iterations) == ("approved", 1)


async def test_improves_until_threshold() -> None:
    conf = cfg()
    _, st = await collect(build_graph(make_agents(["A", "B"], [c(5), c(9)]), conf), "Q")
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


async def test_critic_invalid_raises() -> None:
    agents = make_agents(["A"], [UnexpectedModelBehavior("bad json")])
    with pytest.raises(CriticInvalidError):
        await collect(build_graph(agents, cfg()), "Q")


def test_select_final_pure() -> None:
    assert select_final(["a", "b", "c"], [c(5), c(8), c(8)], approved=False) == ("c", 2)
    assert select_final(["a", "b"], [c(9), c(2)], approved=True) == ("b", 1)


def test_is_approved() -> None:
    assert is_approved(c(3, approved=True), 8)
    assert is_approved(c(8), 8)
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
