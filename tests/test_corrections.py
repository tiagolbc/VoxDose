"""Regressions for the Windows screenshots and export failures reported by the user."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMessageBox,QLabel,QDialog
from PySide6.QtGui import QPalette,QFontDatabase
from voxdose.app import MainWindow
from voxdose.theme import palette
from voxdose.core import Config,Result,analyze,window_summary
from voxdose.plots import supported_window_track,thin,export_summary_table,dashboard
import soundfile as sf

@pytest.fixture
def app():
    a=QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    return a

def result(tmp_path):
    fs=16000;t=np.arange(fs*2)/fs
    p=tmp_path/'two_bouts.wav';sf.write(p,np.r_[.1*np.sin(2*np.pi*200*t),np.zeros(fs*2),.1*np.sin(2*np.pi*200*t)],fs)
    return analyze(p,Config(cpps=False,window_s=5))

def test_mean_never_draws_through_silence(tmp_path):
    r=result(tmp_path);x,y=supported_window_track(r,'f0_mean')
    assert np.isnan(y[(x>2.1)&(x<3.9)]).all()
    assert np.isfinite(y).any()

def test_sparse_high_pitch_does_not_make_window_mean(tmp_path):
    r=result(tmp_path);f=r.frames.copy();f['voiced']=False;f['f0_hz']=np.nan
    f.loc[10,['voiced','f0_hz']]=[True,400.]
    r.frames=f;r.windows=window_summary(f,r.acoustic,Config(window_s=5))
    x,y=supported_window_track(r,'f0_mean')
    assert not np.isfinite(y).any()
    assert r.frames.loc[10,'f0_hz']==400  # display guard preserves scientific data

def test_decimation_preserves_pause_boundaries():
    x=np.arange(10000);y=np.ones(10000);y[4501:4504]=np.nan
    xx,yy=thin(x,y,limit=100)
    assert 4501 in xx and 4503 in xx
    assert np.isnan(yy).any()

def test_complete_table_png(tmp_path):
    from PIL import Image
    r=result(tmp_path);p=export_summary_table(r,tmp_path)
    with Image.open(p) as im:
        assert im.width>=2000 and im.height>=2000
        im.verify()

@pytest.mark.parametrize('theme',['light','dark'])
def test_windows_palette_popup_and_info_contrast(app,tmp_path,theme):
    # Simulate the Windows dark palette that exposed the original light-style bug.
    app.setPalette(palette(True));w=MainWindow(settings_path=tmp_path/'prefs.ini');w.theme=theme;w.build();w.show();app.processEvents()
    assert app.palette().color(QPalette.Window).name()==('#f2f6fa' if theme=='light' else '#101e2d')
    text=' '.join(x.text() for x in w.centralWidget().findChildren(QLabel))
    assert 'Pasquale Bottalico' in text and 'Tiago Lima Bicalho Cruz' in text
    assert 'Context. Change.' not in text and 'Contexto. Evolução.' not in text
    box=QMessageBox(w);box.setText('Texto de ajuda / Help text');box.show();app.processEvents()
    assert all(l.palette().color(QPalette.WindowText).name()=='#ffffff' for l in box.findChildren(QLabel) if l.text())
    box.accept();w.close();app.processEvents()

    # A modeless Matplotlib editor belongs to the plot toolbar; it must not
    # inherit that toolbar's white label backgrounds in the dark application.
    w=MainWindow(settings_path=tmp_path/'prefs.ini');w.theme=theme;w.build()
    w.chart.set_figure(dashboard(result(tmp_path),kind='f0'));w.show();app.processEvents()
    w.chart.toolbar.edit_parameters();app.processEvents()
    dialogs=[d for d in w.chart.toolbar.findChildren(QDialog) if d.isVisible()]
    assert dialogs
    for dialog in dialogs:
        labels=[label for label in dialog.findChildren(QLabel) if label.text().strip()]
        assert labels and all(label.palette().color(QPalette.WindowText).name()==(
            '#dce6f0' if theme=='dark' else '#20354a') for label in labels)
        dialog.reject()
    w.close();app.processEvents()

def test_plot_controls_really_enable_manual_layout(app,tmp_path):
    w=MainWindow(settings_path=tmp_path/'prefs.ini');w.chart.set_figure(dashboard(result(tmp_path)))
    assert w.chart.canvas.figure.get_layout_engine() is not None
    w.chart.toolbar.configure_subplots();app.processEvents()
    assert w.chart.canvas.figure.get_layout_engine() is None
    w.chart.canvas.figure.subplots_adjust(left=.2)
    assert w.chart.canvas.figure.subplotpars.left==pytest.approx(.2)
    if w.chart.toolbar._subplot_dialog:w.chart.toolbar._subplot_dialog.close()
    w.close();app.processEvents()
