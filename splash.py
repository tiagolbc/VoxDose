from PySide6.QtWidgets import QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QElapsedTimer, QRect

def show_splash_screen(app, duration=4000):
    # Tamanho maior do splash
    width, height = 700, 500
    splash_pixmap = QPixmap(width, height)
    splash_pixmap.fill(QColor("#CDCDC1"))  # Usa a mesma cor da GUI

    painter = QPainter(splash_pixmap)

    # Centraliza a logo na parte superior
    logo = QPixmap("logo.png").scaledToHeight(200, Qt.SmoothTransformation)
    logo_x = (width - logo.width()) // 2
    logo_y = 40
    painter.drawPixmap(logo_x, logo_y, logo)

    # Centraliza o texto no espaço restante abaixo da logo
    painter.setPen(QColor("#333"))
    painter.setFont(QFont("Segoe UI", 12))

    text = (
        "VoxDose – Vocal Dose Analyzer\n\n"
        "Estimate vocal dose from audio recordings of the human voice.\n\n"
        "Based on original MATLAB code by Prof. Dr. Pasquale Bottalico,\n\n"
        "Licensed under the MIT License\n"
        "© 2025 FonoTech Academy"
    )

    # Defina a área onde o texto será desenhado
    text_rect = QRect(
        60,  # margem à esquerda
        logo_y + logo.height() + 20,  # logo + espaçamento
        width - 120,  # largura reduzida para margens
        height - (logo_y + logo.height() + 40)  # altura restante
    )
    painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, text)
    painter.end()

    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    # Garante que o splash permaneça visível pelo tempo desejado
    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < duration:
        app.processEvents()
