import os,time
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import Qt
import pytest
from voxdose.app import MainWindow
from voxdose.core import Config,analyze
import soundfile as sf
import numpy as np

@pytest.fixture(scope='module')
def app():
    app=QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    return app

@pytest.fixture
def window(app,tmp_path):
    w=MainWindow(settings_path=tmp_path/'settings.ini');w.language='pt_BR';w.build();w.show();app.processEvents()
    yield w
    w.close();app.processEvents()

def make_result(tmp_path,name='sample.wav',frequency=180):
    fs=16000;t=np.arange(fs*6)/fs;p=tmp_path/name;sf.write(p,.1*np.sin(2*np.pi*frequency*t),fs)
    return analyze(p,Config(subject='P1',task='tone',device='generated',cpps=False))

def add_result(w,r):
    w.results.append(r);w.selector.addItem(r.label,len(w.results)-1);w.selector.setCurrentIndex(len(w.results))

def test_seven_tabs_and_invalid_actions_disabled(window):
    assert window.tabs.count()==7
    assert not window.run_button.isEnabled()
    assert not window.export_button.isEnabled()

def test_language_switch_preserves_config_and_results(window,tmp_path,app):
    r=make_result(tmp_path);add_result(window,r);window.subject.setText('P_KEEP')
    window.language_combo.setCurrentIndex(1);window.apply_settings();app.processEvents()
    assert window.tabs.tabText(0)=='01  Analysis'
    assert window.subject.text()=='P_KEEP'
    assert window.current_result() is r
    assert window.dose_table.rowCount()>30

def test_disable_tutorials_and_persistence(window,app):
    window.tutorial_check.setChecked(False);window.apply_settings();app.processEvents()
    assert not any(b.isVisible() for b in window.info_buttons)
    assert all(not w.toolTip() for w,_ in window.help_widgets)
    assert not window.settings.value('tutorials',True,type=bool)

def test_interval_table_and_search(window,tmp_path):
    r=make_result(tmp_path);add_result(window,r)
    window.range_start.setValue(1);window.range_end.setValue(2.5);window.apply_interval()
    assert window.display_summary['duration_s']==pytest.approx(1.5)
    window.metric_search.setText('CPPS')
    visible=[window.dose_table.item(i,0).text() for i in range(window.dose_table.rowCount()) if not window.dose_table.isRowHidden(i)]
    assert visible==['CPPS · janelas de 5 s']

def test_comparison_withholds_mismatched_subject(window,tmp_path):
    a=make_result(tmp_path,'a.wav');b=make_result(tmp_path,'b.wav',200);b.metadata['config']['subject']='P2'
    add_result(window,a);add_result(window,b);window.update_comparison()
    assert 'participante' in window.compare_note.text()
    assert all(window.compare_table.item(i,4).text()=='—' for i in range(window.compare_table.rowCount()))

def test_all_plot_choices_render(window,tmp_path,app):
    add_result(window,make_result(tmp_path))
    for i in range(window.plot_kind.count()):
        window.plot_kind.setCurrentIndex(i);window.render_chart();app.processEvents()
        assert len(window.chart.canvas.figure.axes)>=1

def test_worker_finishes_without_freezing_event_loop(window,tmp_path,app):
    r=make_result(tmp_path);ticks=[]
    window.start_job(lambda job:(time.sleep(.05),job.note.emit('done')))
    end=time.monotonic()+5
    while window.job.isRunning() and time.monotonic()<end:
        app.processEvents();ticks.append(1);time.sleep(.005)
    app.processEvents()
    assert not window.job.isRunning() and len(ticks)>2
    assert window.analysis_status.text()=='done'
