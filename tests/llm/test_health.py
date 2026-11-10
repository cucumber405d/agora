import httpx
import pytest

from ibikus.appa.agora.config import ModelConfig
from ibikus.appa.agora.llm.health import HealthIssue, check_models

OLLAMA = {"provider": "ollama", "name": "qwen2.5:7b", "temperature": 0.9}


def _m(**kw: object) -> ModelConfig:
    return ModelConfig.model_validate({**OLLAMA, **kw})


def _client(handler) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _tags(*names: str) -> httpx.Response:
    return httpx.Response(200, json={"models": [{"name": n} for n in names]})


async def test_ollama_ok() -> None:
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        return _tags("qwen2.5:7b")

    async with _client(handler) as c:
        issues = await check_models({"Generator": _m(), "Critic": _m(temperature=0.1)}, client=c)
    assert issues == []
    assert calls == ["http://localhost:11434/api/tags"]  # same endpoint checked once


async def test_ollama_unreachable() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=req)

    async with _client(handler) as c:
        issues = await check_models({"Generator": _m(), "Critic": _m()}, client=c)
    assert len(issues) == 1  # one issue per endpoint, both roles named
    issue = issues[0]
    assert issue.roles == ("Generator", "Critic")
    assert "Ollama is not reachable at http://localhost:11434" in issue.problem
    assert "ollama serve" in issue.hint
    assert "https://ollama.com" in issue.hint


async def test_ollama_custom_base_url() -> None:
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(str(req.url))
        return _tags("qwen2.5:7b")

    async with _client(handler) as c:
        await check_models({"Generator": _m(base_url="http://10.0.0.5:11434/v1/")}, client=c)
    assert seen == ["http://10.0.0.5:11434/api/tags"]


async def test_ollama_model_missing() -> None:
    async with _client(lambda r: _tags("llama3.1:8b")) as c:
        issues = await check_models({"Critic": _m()}, client=c)
    assert issues == [
        HealthIssue(
            roles=("Critic",),
            problem="Model 'qwen2.5:7b' is not available in Ollama",
            hint="Run: ollama pull qwen2.5:7b",
        )
    ]


async def test_ollama_model_without_tag_matches_latest() -> None:
    async with _client(lambda r: _tags("llama3:latest")) as c:
        assert await check_models({"Critic": _m(name="llama3")}, client=c) == []


async def test_ollama_http_error() -> None:
    async with _client(lambda r: httpx.Response(500)) as c:
        issues = await check_models({"Generator": _m()}, client=c)
    assert "HTTP 500" in issues[0].problem


@pytest.mark.parametrize(
    ("provider", "key", "url"),
    [
        ("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/models"),
        ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1/models"),
        ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/key"),
    ],
)
async def test_cloud_invalid_key(provider: str, key: str, url: str) -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(401)

    cfg = ModelConfig.model_validate({"provider": provider, "name": "x/y", "temperature": 0.1})
    async with _client(handler) as c:
        issues = await check_models({"Critic": cfg}, env={key: "bad"}, client=c)
    assert str(seen[0].url) == url
    assert "bad" in (
        seen[0].headers.get("x-api-key", "") + seen[0].headers.get("authorization", "")
    )
    assert issues[0].problem == f"{key} was rejected (HTTP 401)"


async def test_cloud_ok() -> None:
    cfg = ModelConfig(provider="anthropic", name="claude-haiku-4-5", temperature=0.1)
    async with _client(lambda r: httpx.Response(200, json={"data": []})) as c:
        assert await check_models({"Critic": cfg}, env={"ANTHROPIC_API_KEY": "k"}, client=c) == []


async def test_cloud_no_connection() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=req)

    cfg = ModelConfig(provider="anthropic", name="claude-haiku-4-5", temperature=0.1)
    async with _client(handler) as c:
        issues = await check_models({"Critic": cfg}, env={"ANTHROPIC_API_KEY": "k"}, client=c)
    assert issues[0].problem == "No connection to api.anthropic.com"


async def test_cloud_missing_key_no_request() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise AssertionError("must not call the API without a key")

    cfg = ModelConfig(provider="openai", name="gpt-4o-mini", temperature=0.1)
    async with _client(handler) as c:
        issues = await check_models({"Critic": cfg}, env={}, client=c)
    assert issues[0].problem == "OPENAI_API_KEY is not set"
    assert ".env" in issues[0].hint


async def test_openai_compatible_base_url_used() -> None:
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(str(req.url))
        return httpx.Response(200, json={"data": []})

    cfg = ModelConfig(provider="openai", name="m", temperature=0.1, base_url="http://lm:1234/v1")
    async with _client(handler) as c:
        await check_models({"Critic": cfg}, env={"OPENAI_API_KEY": "k"}, client=c)
    assert seen == ["http://lm:1234/v1/models"]
