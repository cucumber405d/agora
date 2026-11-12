"""`agora` command-line entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from ibikus.appa.agora import __version__
from ibikus.appa.agora.config import AppConfig, ConfigError, load_config
from ibikus.appa.agora.llm.health import check_config
from ibikus.appa.agora.logging_setup import setup_logging
from ibikus.appa.agora.observability.langfuse import setup_observability
from ibikus.appa.agora.paths import agora_home
from ibikus.appa.agora.reflection.service import ReflectionService
from ibikus.appa.agora.tui.app import AgoraApp

logger = logging.getLogger(__name__)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agora", description="Reflection agent with a Far-style console UI."
    )
    parser.add_argument("--config", type=Path, help="path to agora.yaml")
    parser.add_argument("--root", type=Path, help="file panel root (default: current dir)")
    parser.add_argument("--version", action="version", version=f"agora {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    load_dotenv(Path.cwd() / ".env")
    # Logging first: Langfuse/OpenTelemetry log export errors and must not hit the terminal.
    log_path = setup_logging(agora_home())
    try:
        config = load_config(args.config)
        observability = setup_observability(config.observability.langfuse)

        def service_factory(cfg: AppConfig) -> ReflectionService:
            return ReflectionService(cfg, observability=observability)

        app = AgoraApp(
            config,
            root=args.root or Path.cwd(),
            service_factory=service_factory,
            observability_state=observability.state,
            health_check=check_config,
        )
    except ConfigError as e:
        print(f"Invalid configuration:\n{e}", file=sys.stderr)
        return 2
    logger.info("Agora %s started, log: %s", __version__, log_path)
    try:
        app.run()
    finally:
        observability.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
