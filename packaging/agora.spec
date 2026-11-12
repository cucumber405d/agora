# PyInstaller spec: onedir build of Agora (dist/agora/agora.exe).
# Build: uv run pyinstaller packaging/agora.spec --noconfirm
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = []
for package in ("ibikus.appa.agora", "markitdown", "magika", "pdfminer", "textual"):
    datas += collect_data_files(package)
# Many dependencies (genai_prices, pydantic_ai, langfuse, ...) read their own version via
# importlib.metadata at import time: ship the metadata of the whole dependency tree.
datas += copy_metadata("agora", recursive=True)

hiddenimports = (
    collect_submodules("ibikus.appa.agora")
    + collect_submodules("textual")
    + collect_submodules("markitdown")
    + collect_submodules("pydantic_ai")
)

a = Analysis(
    [SPECPATH + "/entry.py"],
    pathex=[SPECPATH + "/../src"],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="agora",
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, name="agora")
