from pathlib import Path
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PIL import Image
root=Path(__file__).resolve().parents[1];assets=root/'voxdose'/'assets'
app=QApplication.instance() or QApplication([])
renderer=QSvgRenderer(str(assets/'icon.svg'))
image=QImage(1024,1024,QImage.Format_ARGB32);image.fill(0)
painter=QPainter(image);renderer.render(painter);painter.end();image.save(str(assets/'icon.png'))
Image.open(assets/'icon.png').save(assets/'icon.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
source=root.parent/'Python'/'logo.png'
if source.exists():
    import shutil
    shutil.copy2(source,assets/'original_logo.png')
print('SVG, PNG and multi-size ICO ready. Original logo preserved.')
