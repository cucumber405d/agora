import json
from collections.abc import Sequence
from pathlib import Path

import httpx
import pytest

from ibikus.appa.agora.setup import models as m
from ibikus.appa.agora.setup.presets import load_presets
from ibikus.appa.agora.setup.runner import CommandResult

URL = "http://localhost:11434"


def _preset(pid: str):  # type: ignore[no-untyped-def]
    return next(p for p in load_presets() if p.id == pid)


def test_missing_models_dedup() -> None:
    assert m.missing_models(_preset("light"), []) == ["qwen3:4b"]
    assert m.missing_models(_preset("quality"), ["qwen3:14b"]) == ["qwen3.5:9b"]


def test_missing_models_latest() -> None:
    assert m.missing_models(_preset("light"), ["qwen3:4b"]) == []
    assert m.same_model("llama3", "llama3:latest")
    assert not m.same_model("qwen3:4b", "qwen3:8b")


def _ndjson(lines: list[dict[str, object]]) -> bytes:
    return b"".join(json.dumps(x).encode() + b"\n" for x in lines)


def _client(body: bytes) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/pull"
        assert json.loads(request.content) == {"model": "qwen3:4b", "stream": True}
        return httpx.Response(200, content=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _collect(client: httpx.AsyncClient) -> list[m.PullProgress]:
    async with client:
        return [p async for p in m.pull("qwen3:4b", client, URL)]


async def test_pull_progress_sequence() -> None:
    body = _ndjson(
        [
            {"status": "pulling manifest"},
            {"status": "downloading", "digest": "sha", "total": 100, "completed": 50},
            {"status": "success"},
        ]
    )
    events = await _collect(_client(body))
    assert [e.status for e in events] == ["pulling manifest", "downloading", "success"]
    assert (events[1].completed, events[1].total) == (50, 100)


async def test_pull_error_line() -> None:
    body = _ndjson([{"error": "pull model manifest: file does not exist"}])
    with pytest.raises(m.PullError, match="file does not exist"):
        await _collect(_client(body))


async def test_pull_interrupted() -> None:
    body = _ndjson([{"status": "downloading", "total": 100, "completed": 10}])
    with pytest.raises(m.PullError, match="interrupted"):
        await _collect(_client(body))


async def test_pull_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(m.PullError, match="refused"):
        await _collect(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def _ps(text: str):  # type: ignore[no-untyped-def]
    def run(args: Sequence[str], timeout_s: float) -> CommandResult:
        assert list(args)[-1] == "ps"
        return CommandResult(0, text, "")

    return run


def _gen_ok() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        return httpx.Response(200, json={"response": "ok", "done": True})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


PS_HEADER = "NAME          ID              SIZE     PROCESSOR    CONTEXT    UNTIL\n"


async def test_verify_ok() -> None:
    ps = PS_HEADER + "qwen3.5:9b    abc             8 GB     100% GPU     8192       4 minutes\n"
    async with _gen_ok() as client:
        checks = await m.verify(_preset("quality"), client, URL, _ps(ps), Path("ollama"))
    assert [c.status for c in checks] == ["ok", "ok", "ok"]


async def test_verify_cpu_warns() -> None:
    ps = PS_HEADER + "qwen3.5:9b    abc             8 GB     100% CPU     4096       4 minutes\n"
    async with _gen_ok() as client:
        checks = await m.verify(_preset("quality"), client, URL, _ps(ps), Path("ollama"))
    by_name = {c.name: c for c in checks}
    assert by_name["Processor"].status == "warn"
    assert by_name["Context"].status == "warn"
    assert "8192" in by_name["Context"].detail


async def test_verify_generate_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'qwen3.5:9b' not found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        checks = await m.verify(_preset("quality"), client, URL, _ps(PS_HEADER), Path("ollama"))
    assert checks[0].status == "error"
    assert "not found" in checks[0].detail
