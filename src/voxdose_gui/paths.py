# src/voxdose_gui/paths.py
from __future__ import annotations
from pathlib import Path
import sys

def pkg_root() -> Path:
    # .../src
    return Path(__file__).resolve().parents[1]

def candidates_for_assets() -> list[Path]:
    root = pkg_root()
    cands = [
        root / "assets",                 # src/assets  (estrut. de dev)
        Path.cwd() / "assets",           # assets no CWD (rodando via python arquivo.py)
    ]
    # PyInstaller (_MEIPASS)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(Path(meipass) / "assets")
    # Fallback: pasta do módulo
    cands.append(Path(__file__).resolve().parent / "assets")
    # Remover duplicados mantendo ordem
    out, seen = [], set()
    for p in cands:
        s = str(p.resolve())
        if s not in seen:
            out.append(p)
            seen.add(s)
    return out

def asset_path(name: str) -> Path:
    for base in candidates_for_assets():
        p = base / name
        if p.exists():
            return p
    # último fallback: retorna onde deveria estar em dev
    return pkg_root() / "assets" / name
