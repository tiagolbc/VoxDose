from PySide6.QtWidgets import QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QElapsedTimer, QRect

def show_splash_screen(app, duration=4000):
    # Larger splash size
    width, height = 700, 500
    splash_pixmap = QPixmap(width, height)
    splash_pixmap.fill(QColor("#CDCDC1"))  # Usa a mesma cor da GUI

    painter = QPainter(splash_pixmap)

    # Center the logo at the top
    logo = QPixmap("logo.png").scaledToHeight(200, Qt.SmoothTransformation)
    logo_x = (width - logo.width()) // 2
    logo_y = 40
    painter.drawPixmap(logo_x, logo_y, logo)

    # Centers the text in the remaining space below the logo
    painter.setPen(QColor("#333"))
    painter.setFont(QFont("Segoe UI", 12))

    text = (
        "VoxDose – Vocal Dose Analyzer\n\n"
        "Estimate vocal dose from audio recordings of the human voice.\n\n"
        "Based on original MATLAB code by Prof. Dr. Pasquale Bottalico,\n\n"
        "Licensed under the MIT License\n"
        "© 2025 FonoTech Academy"
    )

    # Define the area where the text will be drawn
    text_rect = QRect(
        60,
        logo_y + logo.height() + 20,
        width - 120,
        height - (logo_y + logo.height() + 40)
    )
    painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, text)
    painter.end()

    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < duration:
        app.processEvents()
