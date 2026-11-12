"""PyInstaller entry point (the package's __main__ uses relative-free absolute imports)."""

from ibikus.appa.agora.__main__ import main

raise SystemExit(main())
