"""Local, repeatable checks of the actual application and frozen exports."""
from pathlib import Path
import os,sys,time,json,traceback,hashlib
import numpy as np
import pandas as pd
import soundfile as sf
from PySide6.QtCore import QTimer,Qt,QPointF,QEvent
from PySide6.QtGui import QPalette,QEnterEvent
from PySide6.QtWidgets import QApplication,QMessageBox,QLabel,QScrollArea,QDialog,QToolTip
from PIL import Image
from .core import Config,analyze,Result,window_summary
from .storage import BASE,RESOURCES,load_session,json_text
from .plots import supported_window_track,export_figures,export_summary_table,comparison
from . import __version__

def run_self_test(app,w):
    out=BASE/'verification';out.mkdir(parents=True,exist_ok=True);checks={};failures=[]
    def check(name,value):
        checks[name]=bool(value)
        if not value:failures.append(name)
    def process():app.processEvents()
    def shot(name,widget=None):
        process();(widget or w).grab().save(str(out/(name+'.png')))
    try:
        check('fresh_install_defaults_to_english',w.language=='en_US' and w.tabs.tabText(0)=='01  Analysis')
        # These are synthetic signals with explicit silent intervals, not patient data.
        fs=16000;t=np.arange(fs*4)/fs;voice=.08*np.sin(2*np.pi*200*t)
        audio=np.r_[voice,np.zeros(fs*4),voice]
        audio_path=out/'voice_200Hz_and_silence.wav';sf.write(audio_path,audio,fs)
        cfg=Config(cpps=True,window_s=5,subject='SYNTHETIC',task='verification',device='generated')
        r=analyze(audio_path,cfg)
        check('silence_has_no_f0',not r.frames.loc[(r.frames.center_s>4.1)&(r.frames.center_s<7.9),'voiced'].any())
        xx,yy=supported_window_track(r,'f0_mean')
        check('mean_curve_has_pause_gaps',np.isnan(yy[(xx>4.1)&(xx<7.9)]).all())
        # A window containing one isolated 50 ms candidate must not become a mean curve.
        sparse=r.frames.copy();sparse['voiced']=False;sparse['f0_hz']=np.nan
        sparse.loc[sparse.index[100],['voiced','f0_hz']]=[True,400.]
        sparse_r=Result(r.metadata,sparse,r.acoustic,r.summary,window_summary(sparse,r.acoustic,cfg),[])
        _,sparse_y=supported_window_track(sparse_r,'f0_mean')
        check('isolated_400Hz_candidate_not_a_mean',not np.isfinite(sparse_y).any())
        w.results=[r];w.selector.addItem(r.label,0);w.selector.setCurrentIndex(1);w.populate_comparison()
        for theme in ['light','dark']:
            w.theme=theme;w.loaded_cfg=cfg;w.build();w.show();process()
            check(theme+'_explicit_window_palette',app.palette().color(QPalette.Window).name()==('#101e2d' if theme=='dark' else '#f2f6fa'))
            texts=' '.join(label.text() for label in w.centralWidget().findChildren(QLabel))
            check(theme+'_both_authors_in_header','Pasquale Bottalico' in texts and 'Tiago Lima Bicalho Cruz' in texts)
            check(theme+'_no_commercial_slogan','Context. Change.' not in texts and 'Contexto. Evolução.' not in texts)
            for tab in [0,1,2,3,4,5,6]:
                w.tabs.setCurrentIndex(tab);process();shot(theme+f'_tab_{tab}')
            w.tabs.setCurrentIndex(0);scroll=w.tabs.widget(0).findChild(QScrollArea)
            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());shot(theme+'_groups')
            w.sensor.showPopup();process();shot(theme+'_selection_popup',app.activePopupWidget() or w);w.sensor.hidePopup()
            # Exercise hover help directly, with no click or modal OK dialog.
            scroll.verticalScrollBar().setValue(0);process();info=w.info_buttons[0]
            # Send Qt's hover-entry event directly. Native global mouse motion
            # is verified separately through the desktop UI; background test
            # processes do not reliably receive Windows global cursor events.
            center=QPointF(info.rect().center());origin=QPointF(info.mapToGlobal(info.rect().center()))
            app.sendEvent(info,QEnterEvent(center,center,origin))
            check(theme+'_info_hover_event_visible',QToolTip.isVisible() and bool(QToolTip.text()))
            check(theme+'_info_no_modal_dialog',app.activeModalWidget() is None)
            check(theme+'_info_white_text',QToolTip.palette().color(QPalette.ToolTipText).name()=='#ffffff')
            tips=[widget for widget in app.topLevelWidgets() if widget.isVisible() and widget.windowType()==Qt.ToolTip]
            # Capture synchronously before unrelated native mouse/leave events.
            if tips:tips[0].grab().save(str(out/(theme+'_info_hover.png')))
            app.sendEvent(info,QEvent(QEvent.Leave));QToolTip.hideText();process()
            w.tabs.setCurrentIndex(2);process()
            check(theme+'_toolbar_icons',all(not w.chart.toolbar._actions[n].icon().isNull() for n in ['home','pan','zoom','save_figure']))
            w.chart.toolbar.configure_subplots();process()
            check(theme+'_adjustments_change_layout',w.chart.canvas.figure.get_layout_engine() is None)
            dialogs=[d for d in app.topLevelWidgets() if isinstance(d,QDialog) and d.isVisible() and not isinstance(d,QMessageBox)]
            check(theme+'_plot_adjustments_dialog',bool(dialogs))
            for dialog in dialogs:shot(theme+'_plot_adjustments',dialog);dialog.close()
            w.chart.canvas.figure.subplots_adjust(left=.17)
            check(theme+'_slider_layout_applied',abs(w.chart.canvas.figure.subplotpars.left-.17)<1e-9)
            # Open the full curve editor, not merely Matplotlib's axes chooser.
            w.plot_kind.setCurrentIndex(w.plot_kind.findData('f0'));w.render_chart();process()
            check(theme+'_single_axis_curve_editor',len(w.chart.canvas.figure.axes)==1)
            w.chart.toolbar.edit_parameters();process()
            # FigureOptions is modeless: inspect it before changing the app theme.
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                dialogs=[d for d in app.topLevelWidgets() if isinstance(d,QDialog) and d.isVisible() and not isinstance(d,QMessageBox)]
                if dialogs:break
                process();time.sleep(.01)
            check(theme+'_plot_options_dialog',bool(dialogs))
            for dialog in dialogs:
                labels=[label for label in dialog.findChildren(QLabel) if label.text().strip()]
                expected='#dce6f0' if theme=='dark' else '#20354a'
                check(theme+'_plot_options_theme_consistent',bool(labels) and all(
                    label.palette().color(QPalette.WindowText).name()==expected for label in labels))
                shot(theme+'_plot_options',dialog);dialog.reject()
            w.tabs.setCurrentIndex(4);process();shot(theme+'_diary_toolbar')
        w.language_combo.setCurrentIndex(w.language_combo.findData('pt_BR'));w.apply_settings();process()
        check('portuguese_switch',w.tabs.tabText(0)=='01  Análise')
        w.language_combo.setCurrentIndex(w.language_combo.findData('en_US'));w.apply_settings();process()
        check('english_switch',w.tabs.tabText(0)=='01  Analysis')
        shot('english_header')
        # Exercise the real asynchronous export button path, including dynamic backends.
        exported=[];errors=[]
        w.on_error=lambda text:errors.append(text)
        w.start_job_original=w.start_job
        def watch(fn):
            w.start_job_original(fn);w.job.item.connect(lambda item:exported.append(item))
            w.job.error.connect(lambda text:errors.append(text))
        w.start_job=watch
        w.export_button.click();deadline=time.monotonic()+180
        while w.job and w.job.isRunning() and time.monotonic()<deadline:
            process();time.sleep(.01)
        process();check('export_worker_finished',not w.job.isRunning());check('export_has_no_error',not errors)
        folders=[Path(item[1]) for item in exported if item[0]=='exported']
        check('export_button_completed',bool(folders))
        if folders:
            folder=folders[-1]
            check('summary_png',bool((folder/'VoxDose_results.png').is_file()))
            check('excel',bool((folder/'VoxDose_results.xlsx').is_file()))
            pngs=list((folder/'figures').glob('*.png'));svgs=list((folder/'figures').glob('*.svg'))
            check('all_14_pngs_and_svgs',len(pngs)==14 and len(svgs)==14)
            for png in pngs+[folder/'VoxDose_results.png']:
                with Image.open(png) as im:im.verify()
            check('pngs_decode',True)
            for svg in svgs:
                import xml.etree.ElementTree as ET
                ET.parse(svg)
            check('svgs_parse',True)
            from openpyxl import load_workbook
            book=load_workbook(folder/'VoxDose_results.xlsx',read_only=True)
            check('excel_readable','Summary' in book.sheetnames);book.close()
            loaded=load_session(folder/'session.voxdose');check('session_roundtrip',abs(loaded.summary['dc_cycles']-r.summary['dc_cycles'])<1e-6)
        check('manuals_embedded',all((RESOURCES/'docs'/n).is_file() for n in ['Manual_pt_BR.pdf','Manual_en.pdf']))
        check('svg_backend_importable',__import__('importlib').util.find_spec('matplotlib.backends.backend_svg') is not None)
        check('runtime_python_exists',any(Path(getattr(sys,'_MEIPASS','')).rglob('python3*.dll')) if getattr(sys,'frozen',False) and sys.platform=='win32' else True)
        for required in ['light_plot_options_dialog','dark_plot_options_dialog']:
            if required not in checks:check(required,False)
        result={'ok':not failures,'version':__version__,'frozen':bool(getattr(sys,'frozen',False)),
            'executable':sys.executable,'runtime_extraction':getattr(sys,'_MEIPASS',None),
            'pythonpath':os.environ.get('PYTHONPATH'),'path':os.environ.get('PATH'),
            'checks':checks,'failures':failures,'export_folders':[str(p) for p in folders]}
        (out/'result.json').write_text(json_text(result),encoding='utf-8')
    except Exception:
        (out/'result.json').write_text(json_text({'ok':False,'checks':checks,'failures':failures,
            'exception':traceback.format_exc(),'frozen':bool(getattr(sys,'frozen',False))}),encoding='utf-8')
    finally:
        if w.job and w.job.isRunning():w.job.cancel.set();w.job.wait(10000)
        app.exit(0 if (out/'result.json').exists() and json.loads((out/'result.json').read_text(encoding='utf-8'))['ok'] else 1)
