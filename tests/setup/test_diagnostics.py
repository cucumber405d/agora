from collections.abc import Sequence
from pathlib import Path

import httpx
import pytest

from ibikus.appa.agora.setup import diagnostics as d
from ibikus.appa.agora.setup.runner import CommandResult

SAMPLES = Path(__file__).parent / "samples"


def _sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


def test_parse_nvidia_one() -> None:
    gpu = d.parse_nvidia_smi(_sample("nvidia_smi_one.txt"))
    assert gpu is not None
    assert gpu.name == "NVIDIA GeForce RTX 4070"
    assert gpu.vram_gb == pytest.approx(12.0, abs=0.01)


def test_parse_nvidia_picks_largest() -> None:
    gpu = d.parse_nvidia_smi(_sample("nvidia_smi_two.txt"))
    assert gpu is not None and gpu.name == "NVIDIA GeForce RTX 3090"


def test_parse_nvidia_garbage_returns_none() -> None:
    assert d.parse_nvidia_smi("Failed to initialize NVML: Driver/library version mismatch") is None


def test_parse_ollama_ps() -> None:
    models = d.parse_ollama_ps(_sample("ollama_ps.txt"))
    assert models[0] == d.LoadedModel("qwen3:14b", "100% GPU", 8192)
    assert models[1].name == "qwen3:4b"
    assert models[1].context == 4096


def test_parse_ollama_ps_empty() -> None:
    assert d.parse_ollama_ps("NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\n") == []


def _runner(responses: dict[str, CommandResult]) -> d.Runner:
    def run(args: Sequence[str], timeout_s: float) -> CommandResult:
        return responses.get(args[0], CommandResult(127, "", "not found"))

    return run


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def _ollama_up(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/version":
        return httpx.Response(200, json={"version": "0.12.3"})
    if request.url.path == "/api/tags":
        return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}, {"name": "qwen3:14b"}]})
    return httpx.Response(404)


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused")


def _check(report: d.SystemReport, name: str) -> d.Check:
    return next(c for c in report.checks if c.name == name)


async def test_collect_no_nvidia_smi_uses_windows_name(tmp_path: Path) -> None:
    runner = _runner({"powershell": CommandResult(0, "Intel(R) UHD Graphics\r\n", "")})
    async with _client(_ollama_up) as client:
        report = await d.collect(runner=runner, client=client, env={}, platform="win32")
    assert report.gpu == d.Gpu("Intel(R) UHD Graphics", None)
    assert _check(report, "GPU").status == "warn"


async def test_collect_nvidia_smi_error_is_warning() -> None:
    runner = _runner({"nvidia-smi": CommandResult(9, "", "NVML error")})
    async with _client(_ollama_up) as client:
        report = await d.collect(runner=runner, client=client, env={}, platform="linux")
    assert report.gpu is None
    assert _check(report, "GPU").status == "warn"


async def test_collect_nvidia_ok() -> None:
    runner = _runner({"nvidia-smi": CommandResult(0, _sample("nvidia_smi_one.txt"), "")})
    async with _client(_ollama_up) as client:
        report = await d.collect(runner=runner, client=client, env={}, platform="win32")
    assert report.gpu is not None and report.gpu.vram_gb == pytest.approx(12.0, abs=0.01)
    assert _check(report, "GPU").status == "ok"


async def test_collect_ollama_running() -> None:
    async with _client(_ollama_up) as client:
        report = await d.collect(runner=_runner({}), client=client, env={}, platform="linux")
    assert report.ollama.running is True
    assert report.ollama.version == "0.12.3"
    assert report.ollama.models == ("qwen3:4b", "qwen3:14b")
    assert _check(report, "Ollama").status == "ok"


async def test_collect_ollama_down() -> None:
    async with _client(_down) as client:
        report = await d.collect(runner=_runner({}), client=client, env={}, platform="linux")
    assert report.ollama.running is False
    assert _check(report, "Ollama").status == "error"
    assert report.worst == "error"


async def test_collect_network_false_skips_http() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP expected")

    async with _client(boom) as client:
        report = await d.collect(
            runner=_runner({}), client=client, env={}, platform="linux", network=False
        )
    assert report.ollama.running is False
    assert _check(report, "Ollama").status == "warn"


async def test_collect_reads_ollama_env() -> None:
    env = {"OLLAMA_CONTEXT_LENGTH": "8192", "OLLAMA_KV_CACHE_TYPE": "q8_0", "OTHER": "x"}
    async with _client(_ollama_up) as client:
        report = await d.collect(runner=_runner({}), client=client, env=env, platform="linux")
    assert report.ollama.env == {"OLLAMA_CONTEXT_LENGTH": "8192", "OLLAMA_KV_CACHE_TYPE": "q8_0"}


async def test_check_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> object:
        raise RuntimeError("psutil broken")

    monkeypatch.setattr(d.psutil, "virtual_memory", broken)
    async with _client(_ollama_up) as client:
        report = await d.collect(runner=_runner({}), client=client, env={}, platform="linux")
    assert _check(report, "RAM").status == "warn"
    assert {c.name for c in report.checks} == {"OS", "RAM", "Disk", "GPU", "Ollama"}


def test_models_dir_respects_env(tmp_path: Path) -> None:
    assert d.ollama_models_dir({"OLLAMA_MODELS": str(tmp_path)}) == tmp_path
    assert d.ollama_models_dir({}).parts[-2:] == (".ollama", "models")


def test_find_ollama_exe_in_localappdata(tmp_path: Path) -> None:
    exe = tmp_path / "Programs" / "Ollama" / "ollama.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    assert d.find_ollama_exe({"LOCALAPPDATA": str(tmp_path)}, which=lambda _: None) == exe
    assert d.find_ollama_exe({}, which=lambda _: None) is None
    assert d.find_ollama_exe({}, which=lambda _: "/usr/bin/ollama") == Path("/usr/bin/ollama")


def test_run_command_missing_binary() -> None:
    from ibikus.appa.agora.setup.runner import run_command

    assert run_command(["definitely-not-a-command-xyz"], 5).returncode == 127
