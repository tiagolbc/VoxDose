"""Explicit application palettes, independent of the Windows color scheme."""
from PySide6.QtCore import Qt,QByteArray,QSize
from PySide6.QtGui import QColor,QPalette,QIcon,QPixmap,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QToolTip

def palette(dark=False):
    p=QPalette()
    c={'window':'#101E2D' if dark else '#F2F6FA','base':'#1C3144' if dark else '#FFFFFF',
       'text':'#E3EDF5' if dark else '#20354A','alt':'#20384D' if dark else '#F2F7FA',
       'button':'#243B4F' if dark else '#FFFFFF','muted':'#A2B7C8' if dark else '#64788A',
       'selection':'#176D7B' if dark else '#CDECEF','selected':'#FFFFFF' if dark else '#123F4C'}
    roles={QPalette.Window:c['window'],QPalette.WindowText:c['text'],QPalette.Base:c['base'],
       QPalette.AlternateBase:c['alt'],QPalette.Text:c['text'],QPalette.Button:c['button'],
       QPalette.ButtonText:c['text'],QPalette.BrightText:'#FFFFFF',QPalette.Highlight:c['selection'],
       QPalette.HighlightedText:c['selected'],QPalette.ToolTipBase:'#142D3F',QPalette.ToolTipText:'#FFFFFF',
       QPalette.PlaceholderText:c['muted'],QPalette.Link:'#39B9BF' if dark else '#087F8C',
       QPalette.LinkVisited:'#A995E7' if dark else '#6757C8',QPalette.Light:'#567086' if dark else '#FFFFFF',
       QPalette.Midlight:'#3E586E' if dark else '#E5EDF3',QPalette.Mid:'#567086' if dark else '#B7C7D3',
       QPalette.Dark:'#0A1520' if dark else '#8499AA',QPalette.Shadow:'#07101B',QPalette.Accent:'#087F8C'}
    for group in [QPalette.Active,QPalette.Inactive,QPalette.Disabled]:
        for role,value in roles.items():p.setColor(group,role,QColor(value))
    for role in [QPalette.Text,QPalette.WindowText,QPalette.ButtonText]:
        p.setColor(QPalette.Disabled,role,QColor('#8DA3B5' if dark else '#687F91'))
    return p

def apply_palette(app,dark=False):
    app.setStyle('Fusion')
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light)
    # Native tooltip animation otherwise delays visibility by several hundred
    # milliseconds. Context help should appear immediately on hover/focus.
    app.setEffectEnabled(Qt.UI_AnimateTooltip,False)
    app.setEffectEnabled(Qt.UI_FadeTooltip,False)
    p=palette(dark);app.setPalette(p);QToolTip.setPalette(p)

FINAL_STYLES='''
QMessageBox {background:#142D3F;}
QMessageBox QLabel {color:#FFFFFF;background:transparent;}
QMessageBox QPushButton {background:#FFFFFF;color:#20354A;border:1px solid #B8CBD8;min-width:65px;}
QToolTip {color:#FFFFFF;background:#142D3F;border:1px solid #39596F;}
QLabel#info {color:#FFFFFF;background:#087F8C;font-weight:700;}
QLabel#info:hover,QLabel#info:focus {background:#065D68;}
'''

PATHS={
'home':'M3 11 L12 3 L21 11 M6 10 V21 H10 V15 H14 V21 H18 V10',
'back':'M20 12 H4 M10 5 L3 12 L10 19',
'forward':'M4 12 H20 M14 5 L21 12 L14 19',
'pan':'M12 2 V22 M2 12 H22 M8 6 L12 2 L16 6 M8 18 L12 22 L16 18 M6 8 L2 12 L6 16 M18 8 L22 12 L18 16',
'zoom':'M16 16 L22 22 M12 5 V15 M7 10 H17',
'configure_subplots':'M4 3 V21 M12 3 V21 M20 3 V21 M1 8 H7 M9 16 H15 M17 7 H23',
'edit_parameters':'M3 21 V3 H22 M5 17 L10 12 L14 15 L21 5',
'save_figure':'M3 3 H18 L21 6 V21 H3 Z M7 3 V9 H17 V3 M7 21 V14 H17 V21',
}
def toolbar_icon(name):
    path=PATHS[name];extra='<circle cx="12" cy="10" r="8"/>' if name=='zoom' else ''
    icon=QIcon()
    for mode,color in [(QIcon.Normal,'#20354A'),(QIcon.Active,'#087F8C'),(QIcon.Selected,'#087F8C'),(QIcon.Disabled,'#8193A2')]:
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="{path}"/>{extra}</g></svg>'
        pix=QPixmap(32,32);pix.fill(Qt.transparent);paint=QPainter(pix)
        QSvgRenderer(QByteArray(svg.encode())).render(paint);paint.end();icon.addPixmap(pix,mode)
    return icon
