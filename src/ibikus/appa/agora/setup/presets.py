"""Configuration presets and the choice of the recommended one for this machine."""

from __future__ import annotations

from collections.abc import Sequence
from importlib import resources

import yaml
from pydantic import BaseModel, ConfigDict

from .diagnostics import SystemReport

DISK_RESERVE_GB = 2


class Preset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    generator: str
    critic: str
    download_gb: float
    min_ram_gb: float | None = None
    min_vram_gb: float | None = None
    ollama_context: int
    max_total_tokens: int

    @property
    def models(self) -> list[str]:
        return list(dict.fromkeys([self.generator, self.critic]))


def load_presets() -> list[Preset]:
    """Presets from the bundled presets.yaml, weakest first."""
    text = (resources.files(__package__) / "presets.yaml").read_text(encoding="utf-8")
    return [Preset.model_validate(item) for item in yaml.safe_load(text)]


def unmet(preset: Preset, report: SystemReport) -> list[str]:
    """Human-readable requirements of `preset` this machine does not meet."""
    reasons = []
    if preset.min_ram_gb is not None and report.ram_gb < preset.min_ram_gb:
        reasons.append(f"needs {preset.min_ram_gb:g} GB RAM (found {report.ram_gb:.1f})")
    if preset.min_vram_gb is not None:
        vram = report.gpu.vram_gb if report.gpu else None
        if report.gpu is not None and vram is None:
            reasons.append("GPU memory unknown")
        elif (vram or 0) < preset.min_vram_gb:
            reasons.append(f"needs {preset.min_vram_gb:g} GB VRAM (found {vram or 0:.1f})")
    return reasons


def recommend(presets: Sequence[Preset], report: SystemReport) -> Preset | None:
    """The strongest preset whose requirements are all met, or None."""
    fitting = [p for p in presets if not unmet(p, report)]
    return fitting[-1] if fitting else None


def default_choice(presets: Sequence[Preset], report: SystemReport) -> Preset:
    return recommend(presets, report) or presets[0]


def disk_shortfall_gb(preset: Preset, report: SystemReport) -> float:
    """How many GB are missing to download the preset (with a small reserve)."""
    return max(0.0, preset.download_gb + DISK_RESERVE_GB - report.free_disk_gb)
