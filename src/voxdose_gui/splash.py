# voxdose_gui/splash.py
from pathlib import Path
from PySide6.QtCore import Qt, QElapsedTimer, QRect
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QSplashScreen

# Match GUI logic exactly
PKG_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PKG_ROOT / "assets"

def _resolve_asset(name: str) -> str:
    """
    Same logic as in voxdose_app._resolve_asset:
    1) src/assets/name
    2) packaged asset via asset_path(name)
    3) current working dir (last resort)
    """
    # 1) src/assets
    p1 = ASSETS_DIR / name
    if p1.exists():
        return str(p1)

    # 2) packaged resource (mirroring the GUI helper)
    # We import lazily to avoid circular import
    try:
        from voxdose_gui.paths import asset_path
        p2 = Path(asset_path(name))
        if p2.exists():
            return str(p2)
    except Exception:
        pass

    # 3) fallback to CWD
    return str(Path(name))


def show_splash_screen(app, duration=4000):
    """Show splash screen using the same asset resolution as the GUI."""
    if duration <= 0:
        return

    width, height = 700, 500
    splash_pixmap = QPixmap(width, height)
    splash_pixmap.fill(QColor("#CDCDC1"))

    painter = QPainter(splash_pixmap)

    # Use same logic for logo as GUI (_resolve_asset)
    logo_path = _resolve_asset("logo.png")
    logo_pixmap = QPixmap(logo_path)
    if not logo_pixmap.isNull():
        logo_pixmap = logo_pixmap.scaledToHeight(200, Qt.SmoothTransformation)
        logo_w = logo_pixmap.width()
        logo_h = logo_pixmap.height()
        logo_x = (width - logo_w) // 2
        logo_y = 40
        painter.drawPixmap(logo_x, logo_y, logo_pixmap)
        text_top = logo_y + logo_h + 20
    else:
        text_top = 60

    painter.setPen(QColor("#333"))
    painter.setFont(QFont("Segoe UI", 12))
    text = (
        "VoxDose – Vocal Dose Analyzer\n\n"
        "Estimate vocal dose from audio recordings of the human voice.\n\n"
        "Based on MATLAB code by Prof. Dr. Pasquale Bottalico.\n\n"
        "Licensed under the MIT License\n"
        "© 2025 FonoTech Academy"
    )
    painter.drawText(QRect(60, text_top, width - 120, height - (text_top + 20)),
                     Qt.AlignCenter | Qt.TextWordWrap, text)
    painter.end()

    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < duration:
        app.processEvents()

    splash.hide()
    splash.deleteLater()
    app.processEvents()
