"""User-visible defaults, nonmodal help and installed data locations."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import pytest
from PySide6.QtCore import QEvent,QPointF
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import QApplication,QToolTip,QPushButton
from PySide6.QtTest import QTest
from voxdose.app import MainWindow,InfoLabel
from voxdose.storage import data_directory

@pytest.fixture
def app():return QApplication.instance() or QApplication([])

def test_english_default_and_explicit_portuguese_persists(app,tmp_path):
    prefs=tmp_path/'prefs.ini';w=MainWindow(settings_path=prefs)
    assert w.language=='en_US' and w.tabs.tabText(0)=='01  Analysis'
    w.language_combo.setCurrentIndex(w.language_combo.findData('pt_BR'));w.apply_settings()
    assert w.tabs.tabText(0)=='01  Análise'
    w.close();w=MainWindow(settings_path=prefs)
    assert w.language=='pt_BR'
    w.close()

@pytest.mark.parametrize('theme',['light','dark'])
def test_info_appears_on_hover_without_click_or_modal(app,tmp_path,theme):
    w=MainWindow(settings_path=tmp_path/'prefs.ini');w.theme=theme;w.build();w.show();app.processEvents()
    info=w.info_buttons[0]
    assert isinstance(info,InfoLabel) and not isinstance(info,QPushButton)
    center=QPointF(info.rect().center());global_center=QPointF(info.mapToGlobal(info.rect().center()))
    app.sendEvent(info,QEnterEvent(center,center,global_center));app.processEvents()
    assert QToolTip.isVisible() and 'pseudonymous' in QToolTip.text()
    assert app.activeModalWidget() is None
    app.sendEvent(info,QEvent(QEvent.Leave));QTest.qWait(400)
    assert not QToolTip.isVisible()
    w.tutorial_check.setChecked(False);w.apply_settings();app.processEvents()
    assert all(not icon.isVisible() for icon in w.info_buttons)
    assert all(not field.toolTip() for field,_ in w.help_widgets)
    w.close()

def test_installed_and_macos_data_stay_outside_application(tmp_path):
    executable=tmp_path/'application'/'VoxDose.exe';executable.parent.mkdir()
    environment={'LOCALAPPDATA':str(tmp_path/'user_data')}
    assert data_directory(tmp_path,executable,True,'win32',environment,tmp_path)==executable.parent
    (executable.parent/'installed.flag').write_text('installed')
    assert data_directory(tmp_path,executable,True,'win32',environment,tmp_path)==tmp_path/'user_data'/'VoxDose'
    assert data_directory(tmp_path,executable,True,'darwin',{},tmp_path)==tmp_path/'Library'/'Application Support'/'VoxDose'
    override=tmp_path/'explicit'
    assert data_directory(tmp_path,executable,True,'darwin',{'VOXDOSE_DATA_DIR':str(override)},tmp_path)==override
