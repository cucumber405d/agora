"""`agora` command-line entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ibikus.appa.agora import __version__
from ibikus.appa.agora.config import AppConfig, ConfigError, find_config_path, load_config
from ibikus.appa.agora.context.documents import ConversionError, DocumentConverter
from ibikus.appa.agora.llm.health import check_config
from ibikus.appa.agora.logging_setup import setup_logging
from ibikus.appa.agora.observability.langfuse import setup_observability
from ibikus.appa.agora.paths import agora_home
from ibikus.appa.agora.reflection.service import ReflectionService
from ibikus.appa.agora.setup.cli import doctor
from ibikus.appa.agora.setup.config_writer import first_run_config
from ibikus.appa.agora.tui.app import AgoraApp

logger = logging.getLogger(__name__)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agora", description="Reflection agent with a Far-style console UI."
    )
    parser.add_argument("--config", type=Path, help="path to agora.yaml")
    parser.add_argument("--root", type=Path, help="file panel root (default: current dir)")
    parser.add_argument("--version", action="version", version=f"agora {__version__}")
    sub = parser.add_subparsers(dest="command")
    doctor = sub.add_parser("doctor", help="print system and Ollama diagnostics")
    doctor.add_argument("--no-network", action="store_true", help="skip Ollama and internet checks")
    sub.add_parser("setup", help="open the setup wizard")
    convert = sub.add_parser("convert", help="print the Markdown extracted from a document")
    convert.add_argument("file", type=Path)
    return parser.parse_args(argv)


def _convert(path: Path) -> int:
    try:
        text = DocumentConverter().to_markdown(path)
    except (ConversionError, OSError) as e:
        print(f"Cannot convert {path}: {e}", file=sys.stderr)
        return 1
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    load_dotenv(Path.cwd() / ".env")
    # Logging first: Langfuse/OpenTelemetry log export errors and must not hit the terminal.
    log_path = setup_logging(agora_home())
    try:
        config_path = find_config_path(args.config, os.environ, Path.cwd())
    except ConfigError as e:
        print(f"Invalid configuration:\n{e}", file=sys.stderr)
        return 2
    if args.command == "convert":
        return _convert(args.file)
    if args.command == "doctor":
        return asyncio.run(doctor(network=not args.no_network, config_path=config_path))
    first_run = config_path is None
    try:
        config = first_run_config() if first_run else load_config(args.config)
        observability = setup_observability(config.observability.langfuse)

        def service_factory(cfg: AppConfig) -> ReflectionService:
            return ReflectionService(cfg, observability=observability)

        app = AgoraApp(
            config,
            root=args.root or Path.cwd(),
            service_factory=service_factory,
            observability_state=observability.state,
            health_check=check_config,
            start_wizard=first_run or args.command == "setup",
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
