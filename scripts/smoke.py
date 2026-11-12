"""Smoke-test a built agora executable: it starts, finds its resources and runs doctor."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(exe: Path, expected_version: str) -> int:
    version = subprocess.run(
        [str(exe), "--version"], capture_output=True, text=True, timeout=120, check=False
    )
    if version.returncode != 0 or f"agora {expected_version}" not in version.stdout:
        print(f"--version failed: rc={version.returncode}\n{version.stdout}{version.stderr}")
        return 1
    doctor = subprocess.run(
        [str(exe), "doctor", "--no-network"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if doctor.returncode not in (0, 1, 2) or "Traceback" in doctor.stderr:
        print(f"doctor failed: rc={doctor.returncode}\n{doctor.stdout}{doctor.stderr}")
        return 1
    if "Configurations:" not in doctor.stdout:  # presets.yaml was bundled
        print(f"doctor output incomplete:\n{doctor.stdout}")
        return 1
    print(doctor.stdout)
    fixtures = Path(__file__).parent.parent / "tests" / "fixtures" / "docs"
    for name, marker in (("sample.pdf", "PDF"), ("sample.docx", "DOCX"), ("sample.xlsx", "XLSX")):
        conv = subprocess.run(
            [str(exe), "convert", str(fixtures / name)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        if conv.returncode != 0 or f"Agora sample document {marker}" not in conv.stdout:
            print(f"convert {name} failed: rc={conv.returncode}\n{conv.stdout}{conv.stderr}")
            return 1
    print("smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2]))
