"""Explicitly synthetic examples and real application screenshots for the manuals."""
import os,sys,copy,json
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import numpy as np
import soundfile as sf
from PySide6.QtWidgets import QApplication,QScrollArea,QGroupBox
from PySide6.QtGui import QFontDatabase,QFont
from PySide6.QtCore import Qt
from voxdose.core import Config,analyze
from voxdose.storage import save_session,export_tables
from voxdose.plots import export_figures
from voxdose.app import MainWindow
examples=root/'examples';examples.mkdir(exist_ok=True)
shots=root/'docs'/'images';shots.mkdir(parents=True,exist_ok=True)
fs=16000
t=np.arange(fs*3)/fs
cal=.08*(np.sin(2*np.pi*180*t)+.25*np.sin(4*np.pi*180*t))
sf.write(examples/'synthetic_calibration.wav',cal,fs)
results=[]
for i,(name,duration,fund,amp) in enumerate([('Synthetic_A',180,175,.065),('Synthetic_B',240,195,.09)]):
    t=np.arange(duration*fs)/fs
    f0=fund+18*np.sin(2*np.pi*t/17)+8*np.sin(2*np.pi*t/3)
    phase=2*np.pi*np.cumsum(f0)/fs
    duty=np.mod(t,6.5)<(3.6+i*.4)
    envelope=np.minimum(1,np.mod(t,6.5)*15)*np.minimum(1,np.maximum(0,(3.6+i*.4)-np.mod(t,6.5))*15)
    x=amp*(np.sin(phase)+.35*np.sin(2*phase)+.12*np.sin(3*phase))*duty*envelope
    sf.write(examples/(name+'.flac'),x,fs)
    cfg=Config(calibration=[{'path':str(examples/'synthetic_calibration.wav'),'level':75.}],
        subject='SYNTHETIC_DEMO',task='synthetic voiced signal',device='generated, identical setup',window_s=15)
    r=analyze(examples/(name+'.flac'),cfg)
    r.metadata['notes_demo']='Artificial data for interface tutorials, not a human recording or clinical validation.'
    r.metadata['diary']=[{'timestamp':'2026-11-15T09:00:00-03:00','phase':'before','effort':1.,'fatigue':1.,'discomfort':0.,'notes':'DEMO'},
        {'timestamp':'2026-11-15T09:20:00-03:00','phase':'after','effort':4.,'fatigue':5.,'discomfort':2.,'notes':'DEMO'},
        {'timestamp':'2026-11-15T12:20:00-03:00','phase':'followup','effort':2.,'fatigue':2.,'discomfort':1.,'notes':'DEMO'}]
    save_session(r,examples/(name+'.voxdose'));results.append(r)
export_tables(results[0],examples/'export_example')
export_figures(results[0],examples/'export_example'/'figures','pt_BR',True)
app=QApplication.instance() or QApplication([])
for name in ['segoeui.ttf','segoeuib.ttf','seguisb.ttf','segoeuii.ttf','seguisym.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setFont(QFont('Segoe UI',10));app.setStyle('Fusion')
for language,prefix in [('pt_BR','pt'),('en_US','en')]:
    w=MainWindow(settings_path=root/'validation'/'screenshots_settings.ini');w.language=language;w.loaded_cfg=Config(**results[0].metadata['config']);w.build()
    w.resize(1280,940);w.files=[str(examples/'Synthetic_A.flac'),str(examples/'Synthetic_B.flac')];w.refresh_queue()
    for r in results:
        w.results.append(r);w.result_paths[id(r)]=str(examples);w.selector.addItem(r.label,len(w.results)-1)
    w.selector.setCurrentIndex(1);w.populate_comparison();w.show()
    for page in range(7):
        w.tabs.setCurrentIndex(page)
        if page==3:w.update_comparison()
        app.processEvents();w.grab().save(str(shots/f'{prefix}_{page+1:02d}.png'))
    w.tabs.setCurrentIndex(0);scroll=w.tabs.widget(0).findChild(QScrollArea)
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());app.processEvents()
    w.grab().save(str(shots/f'{prefix}_detection.png'))
    scroll.verticalScrollBar().setValue(int(scroll.verticalScrollBar().maximum()*.45));app.processEvents()
    w.grab().save(str(shots/f'{prefix}_calibration.png'))
    w.plot_kind.setCurrentIndex(2);w.tabs.setCurrentIndex(2);app.processEvents();w.grab().save(str(shots/f'{prefix}_separate.png'))
    w.theme='dark';w.loaded_cfg=w.read_config();w.build();w.tabs.setCurrentIndex(1);app.processEvents();w.grab().save(str(shots/f'{prefix}_dark.png'))
    w.close();app.processEvents()
(examples/'README.txt').write_text('SYNTHETIC DEMONSTRATION DATA\nAll recordings, calibration values and self-ratings in this directory are artificial.\nThey demonstrate workflow and are not clinical measurements or normative references.\nOpen Synthetic_A.voxdose and Synthetic_B.voxdose to explore comparison without reprocessing.\n',encoding='utf-8')
print('Synthetic examples, all plots and 22 application screenshots generated.')
