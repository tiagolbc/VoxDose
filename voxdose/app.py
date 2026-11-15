"""VoxDose 2.0 desktop workspace. Development: Tiago Lima Bicalho Cruz, UFMG."""
from __future__ import annotations
import sys,os,copy,traceback,threading,json,logging,html
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
import numpy as np
import pandas as pd
import soundfile as sf
from PySide6.QtCore import Qt,QThread,Signal,Slot,QLocale,QUrl,QSettings,QTimer,QSize,QEvent,QPoint
from PySide6.QtGui import QIcon,QFont,QDesktopServices,QKeySequence,QShortcut,QPixmap,QColor
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
    QLabel,QPushButton,QTabWidget,QFrame,QFileDialog,QComboBox,QDoubleSpinBox,QSpinBox,
    QCheckBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QProgressBar,
    QMessageBox,QLineEdit,QTextEdit,QTextBrowser,QScrollArea,QSplitter,QDialog,QDialogButtonBox,
    QFormLayout,QGroupBox,QToolTip)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from matplotlib.figure import Figure
from . import AUTHOR,AFFILIATION,__version__
from .core import Config,Result,analyze,Cancelled,compatibility,summarize
from .storage import BASE,OUTPUT,RESOURCES,save_session,load_session,new_output_folder,export_tables,json_text
from .plots import dashboard,comparison,export_figures,KINDS,level_unit,PALETTE
from .i18n import METRICS,WARNINGS,metric,fmt
from .theme import apply_palette,palette,toolbar_icon,FINAL_STYLES

ASSETS=Path(__file__).resolve().parent/'assets'
LIGHT='''
QWidget {font-family:"Segoe UI","Helvetica Neue","Arial"; font-size:13px; color:#20354A;}
QMainWindow, QWidget#root {background:#F2F6FA;}
QFrame#header {background:#0B2C3D; border-radius:16px;}
QFrame#header QLabel {color:#D5E5EC; background:transparent;}
QLabel#brand {font-size:28px;font-weight:700;color:white;}
QLabel#tag {color:#70E1CF;background:#154555;border-radius:10px;padding:6px 12px;font-weight:600;}
QLabel#heading {font-size:21px;font-weight:650;}
QLabel#muted {color:#64788A;}
QLabel#section {font-size:15px;font-weight:650;}
QFrame#card,QGroupBox {background:#FFFFFF;border:1px solid #DEE7EF;border-radius:12px;}
QGroupBox {margin-top:14px;padding:18px 12px 12px;font-weight:600;}
QGroupBox::title {subcontrol-origin:margin;left:14px;top:3px;}
QPushButton {background:#FFFFFF;border:1px solid #CEDBE5;border-radius:7px;padding:9px 14px;font-weight:600;}
QPushButton:hover {background:#E8F3F5;border-color:#13939D;}
QPushButton:pressed {background:#D2E9EB;}
QPushButton:disabled {background:#E9EFF4;color:#9AA8B4;border-color:#DEE5EC;}
QPushButton#primary {background:#087F8C;border:1px solid #087F8C;color:white;}
QPushButton#primary:hover {background:#096B77;}
QPushButton#primary:disabled {background:#A2C3C7;border-color:#A2C3C7;}
QLabel#info {padding:0px;border-radius:10px;background:#E8F4F5;color:#087F8C;border:0;font-size:12px;}
QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QTextEdit,QTextBrowser {background:#FFFFFF;border:1px solid #CEDBE5;border-radius:6px;padding:7px;selection-background-color:#087F8C;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {border:1px solid #087F8C;}
QComboBox::drop-down {border:0;width:24px;}
QTabWidget::pane {background:#FFFFFF;border:1px solid #DEE7EF;border-radius:10px;top:-1px;}
QTabBar::tab {padding:12px 18px;background:#E9EFF5;border:0;margin:0px 3px 6px 0;border-radius:7px;color:#637487;font-weight:600;}
QTabBar::tab:selected {background:#087F8C;color:#FFFFFF;}
QTabBar::tab:hover:!selected {background:#DCEAEF;}
QTableWidget {background:white;alternate-background-color:#F4F8FB;border:1px solid #E1E9EF;border-radius:7px;gridline-color:#E8EEF3;selection-background-color:#D8EFF0;selection-color:#174754;}
QHeaderView::section {background:#EDF3F7;color:#496174;font-weight:600;border:0;border-bottom:1px solid #D9E4EC;padding:10px 7px;}
QTableWidget::item {padding:7px;}
QProgressBar {background:#E4EDF3;border:0;border-radius:5px;text-align:center;height:17px;color:#224554;}
QProgressBar::chunk {background:#30B5B6;border-radius:5px;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:#EFF3F6;width:10px;margin:0;}
QScrollBar::handle:vertical {background:#C1D1DC;min-height:30px;border-radius:4px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QCheckBox {spacing:7px;}
QCheckBox::indicator {width:17px;height:17px;}
QToolTip {background:#0B2C3D;color:white;border:0;padding:9px;}
QSplitter::handle {background:#F2F6FA;width:10px;}
QDialog {background:#F2F6FA;}
QGroupBox::title {color:#20354A;background:#FFFFFF;padding:2px 5px;}
QComboBox QAbstractItemView {background:#FFFFFF;color:#20354A;selection-background-color:#CDECEF;selection-color:#123F4C;border:1px solid #CEDBE5;}
QAbstractItemView::item:selected {background:#CDECEF;color:#123F4C;}
QAbstractItemView::item:selected:!active {background:#CDECEF;color:#123F4C;}
QLineEdit,QTextEdit,QDoubleSpinBox,QSpinBox {selection-background-color:#087F8C;selection-color:#FFFFFF;}
'''
DARK='''
QWidget {color:#DCE6F0;}
QMainWindow,QWidget#root {background:#101E2D;}
QFrame#card,QGroupBox,QTabWidget::pane {background:#172A3C;border-color:#2B4356;}
QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QTextEdit,QTextBrowser {background:#1C3144;color:#DCE6F0;border-color:#385065;}
QPushButton {background:#243B4F;color:#E2EDF4;border-color:#3A5266;}
QPushButton:hover {background:#315367;}
QTabBar::tab {background:#20364A;color:#B2C7D5;}
QTableWidget {background:#172A3C;alternate-background-color:#1D3246;color:#DCE6F0;border-color:#2B4356;selection-background-color:#245667;selection-color:white;}
QHeaderView::section {background:#243B4F;color:#C9DCE8;border-color:#385065;}
QLabel#muted {color:#A5BDCD;}
QProgressBar {background:#243B4F;color:white;}
QScrollBar:vertical,QSplitter::handle {background:#101E2D;}
QDialog {background:#101E2D;}
QGroupBox::title {background:#172A3C;color:#E3EDF5;}
QComboBox QAbstractItemView {background:#1C3144;color:#E3EDF5;selection-background-color:#176D7B;selection-color:#FFFFFF;}
QAbstractItemView::item:selected,QAbstractItemView::item:selected:!active {background:#176D7B;color:#FFFFFF;}
'''

class Job(QThread):
    progress=Signal(int,str)
    item=Signal(object)
    error=Signal(str)
    note=Signal(str)
    def __init__(self,fn,parent=None):
        super().__init__(parent);self.fn=fn;self.cancel=threading.Event()
    def run(self):
        try:self.fn(self)
        except Cancelled:self.note.emit('Cancelado / Cancelled')
        except Exception as e:
            logging.exception('Background operation failed');self.error.emit(str(e))

class SortItem(QTableWidgetItem):
    def __lt__(self,other):
        a=self.data(Qt.UserRole);b=other.data(Qt.UserRole)
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):return a<b
        # Calling the Qt base virtual operator can re-enter this Python override.
        return self.text().casefold()<other.text().casefold()

class ScientificToolbar(NavigationToolbar2QT):
    def __init__(self,canvas,parent):
        super().__init__(canvas,parent)
        self.setPalette(palette(False));self.setIconSize(QSize(23,23));self.setMinimumHeight(40)
        self.setStyleSheet('''QToolBar {background:#FFFFFF;color:#20354A;border:0;spacing:5px;}
QToolBar > QLabel {color:#20354A;background:#FFFFFF;}
QToolBar > QToolButton {color:#20354A;background:#FFFFFF;border:1px solid transparent;border-radius:4px;padding:5px;}
QToolBar > QToolButton:hover,QToolBar > QToolButton:checked {background:#D8EFF0;border:1px solid #087F8C;}
QToolBar > QToolButton:disabled {background:#F5F8FA;color:#687F91;}
QToolBar::separator {background:#CAD6DF;width:1px;margin:7px 4px;}''')
        for name,action in self._actions.items():
            if name in ['home','back','forward','pan','zoom','configure_subplots','edit_parameters','save_figure']:
                action.setIcon(toolbar_icon(name))
        # Matplotlib dialogs inherit the explicit application palette.

    def configure_subplots(self,*args):
        # The automatic layout engine otherwise ignores the user's adjustment sliders.
        self.canvas.figure.set_layout_engine(None)
        return super().configure_subplots(*args)

    def edit_parameters(self,*args):
        result=super().edit_parameters(*args)
        # Matplotlib owns this modeless dialog through the white plot toolbar.
        # Keep the dialog on the application theme rather than inheriting white.
        for dialog in self.findChildren(QDialog):
            dialog.setPalette(QApplication.instance().palette())
        return result

class PlotWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.box=QVBoxLayout(self);self.box.setContentsMargins(0,0,0,0)
        self.canvas=FigureCanvasQTAgg(Figure(facecolor='white'));self.canvas.setMinimumHeight(280)
        self.toolbar=ScientificToolbar(self.canvas,self);self.box.addWidget(self.toolbar);self.box.addWidget(self.canvas,1)
    def set_figure(self,fig):
        old=self.canvas;toolbar=self.toolbar
        self.box.removeWidget(toolbar);self.box.removeWidget(old)
        toolbar.deleteLater();old.figure.clear();old.deleteLater()
        self.canvas=FigureCanvasQTAgg(fig);self.canvas.setMinimumHeight(280)
        self.toolbar=ScientificToolbar(self.canvas,self)
        self.box.addWidget(self.toolbar);self.box.addWidget(self.canvas,1)
        if self.isVisible():self.canvas.draw_idle()

class InfoLabel(QLabel):
    """Immediate contextual help on hover or keyboard focus, without a dialog."""
    def __init__(self,title,helptext,parent=None):
        super().__init__('i',parent)
        self.setObjectName('info');self.setFixedSize(20,20);self.setAlignment(Qt.AlignCenter)
        self.setFocusPolicy(Qt.StrongFocus);self.setCursor(Qt.WhatsThisCursor)
        self.setToolTip('<qt>'+html.escape(helptext)+'</qt>');self.setToolTipDuration(30000)
        self.setAccessibleName(title);self.setAccessibleDescription(helptext)

    def event(self,event):
        if event.type() in (QEvent.Enter,QEvent.FocusIn) and self.isVisible() and self.toolTip():
            QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()+QPoint(0,6)),self.toolTip(),self)
        elif event.type() in (QEvent.Leave,QEvent.FocusOut):
            QToolTip.hideText()
        return super().event(event)

class MainWindow(QMainWindow):
    def __init__(self,settings_path=None):
        super().__init__();BASE.mkdir(parents=True,exist_ok=True)
        self.settings=QSettings(str(settings_path or BASE/'settings.ini'),QSettings.IniFormat)
        self.language=self.settings.value('language','en_US');self.theme=self.settings.value('theme','light')
        self.tutorials=self.settings.value('tutorials',True,type=bool)
        self.files=[];self.results=[];self.result_paths={};self.info_buttons=[];self.help_widgets=[];self.job=None
        self.selected_index=-1;self.plot_dialogs=[];self.loaded_cfg=Config()
        self.setWindowTitle('VoxDose 2.0');self.setWindowIcon(QIcon(str(ASSETS/'icon.svg')))
        self.resize(1440,1000);self.setMinimumSize(1000,740);self.setAcceptDrops(True)
        self.build()
        QShortcut(QKeySequence('Ctrl+O'),self,self.add_files)
        QShortcut(QKeySequence('Ctrl+S'),self,self.save_current)
        QShortcut(QKeySequence('F1'),self,lambda:self.tabs.setCurrentIndex(6))
        self.statusBar().showMessage(self.T('Pronto · processamento local','Ready · local processing'))

    def T(self,pt,en):return pt if self.language=='pt_BR' else en
    def button(self,pt,en,fn,primary=False):
        b=QPushButton(self.T(pt,en));b.clicked.connect(fn)
        if primary:b.setObjectName('primary')
        return b
    def label(self,pt,en,object_name=None):
        x=QLabel(self.T(pt,en));x.setWordWrap(True)
        if object_name:x.setObjectName(object_name)
        return x
    def info(self,title,pt,en):
        row=QWidget();h=QHBoxLayout(row);h.setContentsMargins(0,0,0,0);h.setSpacing(6)
        text=QLabel(title);text.setWordWrap(True);h.addWidget(text)
        helptext=self.T(pt,en);b=InfoLabel(self.T('Informações: ','Information: ')+title,helptext)
        b.setVisible(self.tutorials)
        self.info_buttons.append(b);h.addWidget(b);h.addStretch()
        return row,helptext
    def field(self,form,title,widget,pt,en):
        label,helptext=self.info(title,pt,en);form.addRow(label,widget)
        self.help_widgets.append((widget,helptext));widget.setToolTip(helptext if self.tutorials else '')
    def spin(self,value,lo,hi,step=1,decimals=1,suffix=''):
        s=QDoubleSpinBox();s.setRange(lo,hi);s.setDecimals(decimals);s.setSingleStep(step);s.setValue(value);s.setSuffix(suffix)
        s.setLocale(QLocale('pt_BR' if self.language=='pt_BR' else 'en_US'));s.setMinimumWidth(110);return s
    def combo(self,items,current=None):
        c=QComboBox()
        for label,data in items:c.addItem(label,data)
        if current is not None:c.setCurrentIndex(max(0,c.findData(current)))
        return c
    def card(self):
        f=QFrame();f.setObjectName('card');return f
    def page(self):
        p=QWidget();v=QVBoxLayout(p);v.setContentsMargins(20,18,20,18);v.setSpacing(12);return p,v
    def table(self,columns):
        t=QTableWidget(0,len(columns));t.setHorizontalHeaderLabels(columns);t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False);t.setShowGrid(False);t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers);t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setDefaultSectionSize(42);return t

    def build(self):
        self.info_buttons=[];self.help_widgets=[]
        apply_palette(QApplication.instance(),self.theme=='dark')
        QApplication.instance().setStyleSheet(LIGHT+(DARK if self.theme=='dark' else '')+FINAL_STYLES)
        root=QWidget();root.setObjectName('root');layout=QVBoxLayout(root);layout.setContentsMargins(20,18,20,10);layout.setSpacing(14)
        header=QFrame();header.setObjectName('header');h=QHBoxLayout(header);h.setContentsMargins(20,15,24,15)
        logo=QLabel();logo.setPixmap(QIcon(str(ASSETS/'icon.svg')).pixmap(62,62));h.addWidget(logo)
        names=QVBoxLayout();names.setSpacing(0);names.addWidget(self.label('VoxDose 2.0','VoxDose 2.0','brand'))
        names.addWidget(self.label('Análise de doses vocais','Vocal dose analysis'));h.addLayout(names);h.addStretch()
        author=QVBoxLayout();author.setSpacing(4)
        author.addWidget(self.label('Códigos originais de dosimetria: Pasquale Bottalico','Original dosimetry code: Pasquale Bottalico'))
        author.addWidget(self.label('Adaptação e desenvolvimento do VoxDose: '+AUTHOR,'VoxDose adaptation and development: '+AUTHOR))
        author.addWidget(QLabel(AFFILIATION));h.addLayout(author)
        tag=self.label('2.0  /  PESQUISA','2.0  /  RESEARCH','tag');h.addSpacing(20);h.addWidget(tag);layout.addWidget(header)
        ribbon=QHBoxLayout();ribbon.addWidget(self.label('Sessão ativa','Active session'))
        self.selector=QComboBox();self.selector.setMinimumWidth(270);self.selector.addItem(self.T('Selecione ou analise uma gravação','Select or analyze a recording'),-1)
        for i,r in enumerate(self.results):self.selector.addItem(r.label,i)
        self.selector.setCurrentIndex(self.selected_index+1);self.selector.currentIndexChanged.connect(self.select_result)
        ribbon.addWidget(self.selector,1)
        self.open_button=self.button('Abrir sessão','Open session',self.open_session)
        self.save_button=self.button('Salvar sessão','Save session',self.save_current)
        self.export_button=self.button('Exportar resultados','Export results',self.export_current,True)
        ribbon.addWidget(self.open_button);ribbon.addWidget(self.save_button);ribbon.addWidget(self.export_button);layout.addLayout(ribbon)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        builders=[(self.analysis_page,'01  Análise','01  Analysis'),(self.doses_page,'02  Doses','02  Doses'),
                  (self.charts_page,'03  Gráficos','03  Charts'),(self.compare_page,'04  Comparação','04  Comparison'),
                  (self.diary_page,'05  Diário','05  Diary'),(self.settings_page,'06  Ajustes','06  Settings'),
                  (self.help_page,'07  Guia','07  Guide')]
        for fn,pt,en in builders:self.tabs.addTab(fn(),self.T(pt,en))
        self.tabs.currentChanged.connect(self.tab_changed)
        self.setCentralWidget(root);self.refresh_queue();self.refresh_results();self.update_enabled()

    def analysis_page(self):
        p,v=self.page();split=QSplitter(Qt.Horizontal);v.addWidget(split,1)
        left=QWidget();lv=QVBoxLayout(left);lv.setContentsMargins(0,0,10,0);lv.setSpacing(12)
        lv.addWidget(self.label('Gravações e parâmetros de análise','Recordings and analysis parameters','heading'))
        lv.addWidget(self.label('Adicione uma ou várias gravações. Arraste arquivos para esta janela ou use o botão abaixo.','Add one or more recordings. Drop files onto this window or use the button below.','muted'))
        row=QHBoxLayout();self.add_button=self.button('+ Adicionar áudios','+ Add audio',self.add_files,True)
        self.remove_button=self.button('Remover','Remove',self.remove_files);row.addWidget(self.add_button);row.addWidget(self.remove_button);lv.addLayout(row)
        self.queue=self.table([self.T('Gravação','Recording'),self.T('Duração','Duration'),self.T('Canais','Channels')]);self.queue.setMinimumWidth(310)
        self.queue.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);lv.addWidget(self.queue,1)
        note=self.card();nl=QVBoxLayout(note);nl.addWidget(self.label('COMO PREPARAR','BEFORE YOU START','section'))
        nl.addWidget(self.label('Mantenha o mesmo ganho e canal na calibração e no monitoramento. Identifique participante, tarefa e dispositivo para comparar sessões.','Keep the same gain and channel for calibration and monitoring. Record participant, task and device to compare sessions.','muted'));lv.addWidget(note)
        split.addWidget(left)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setMinimumWidth(500)
        controls=QWidget();cv=QVBoxLayout(controls);cv.setContentsMargins(10,0,2,0);cv.setSpacing(8)
        cfg=self.loaded_cfg
        group=QGroupBox(self.T('Contexto da gravação','Recording context'));form=QFormLayout(group);form.setSpacing(10)
        self.subject=QLineEdit(cfg.subject);self.subject.setPlaceholderText(self.T('Ex.: P001','e.g. P001'))
        self.field(form,self.T('Participante / código','Participant / code'),self.subject,'Use um código pseudonimizado. Comparações diretas exigem o mesmo código.','Use a pseudonymous code. Direct comparisons require the same code.')
        self.task=QLineEdit(cfg.task);self.task.setPlaceholderText(self.T('Ex.: aula, leitura, canto','e.g. teaching, reading, singing'))
        self.field(form,self.T('Tarefa','Task'),self.task,'Descreva o contexto ou tarefa. A tarefa afeta F0, intensidade e CPPS.','Describe the context or task. Task affects F0, intensity and CPPS.')
        self.device=QLineEdit(cfg.device);self.device.setPlaceholderText(self.T('Modelo, ganho, posição / acoplamento','Model, gain, placement / coupling'))
        self.field(form,self.T('Dispositivo e montagem','Device and setup'),self.device,'Identifique sensor, gravador, ganho, posição e fixação. Use a mesma descrição para sessões comparáveis.','Identify sensor, recorder, gain, placement and attachment. Use the same description for comparable sessions.')
        self.notes=QLineEdit(cfg.notes)
        self.field(form,self.T('Observações','Notes'),self.notes,'Anote condições ambientais, intervenções, sintomas ou mudanças de montagem.','Record environmental conditions, interventions, symptoms or setup changes.')
        self.sensor=self.combo([(self.T('Microfone aéreo','Air microphone'),'air'),(self.T('Microfone de contato · experimental','Contact microphone · experimental'),'contact'),(self.T('Acelerômetro · experimental','Accelerometer · experimental'),'accelerometer')],cfg.sensor)
        self.field(form,self.T('Tipo de sensor','Sensor type'),self.sensor,'Contato e acelerômetro não medem pressão acústica diretamente. Para estimar SPL, use ao menos 3 níveis de referência simultânea e preserve o acoplamento.','Contact microphones and accelerometers do not directly measure acoustic pressure. SPL estimation needs at least 3 simultaneous reference levels and unchanged coupling.')
        self.channel=QSpinBox();self.channel.setRange(1,64);self.channel.setValue(cfg.channel+1)
        self.field(form,self.T('Canal do arquivo','File channel'),self.channel,'Seleção explícita: canal 1 é a primeira trilha. Não é feita média nem escolha automática do canal mais alto.','Explicit selection: channel 1 is the first track. No averaging or automatic loudest-channel selection.')
        cv.addWidget(group)
        group=QGroupBox(self.T('Calibração de intensidade','Intensity calibration'));form=QFormLayout(group);form.setSpacing(10)
        self.cal_weight=self.combo([('dBA','A'),('dB SPL Z','Z')],cfg.calibration_weighting)
        self.field(form,self.T('Ponderação do sonômetro','Sound level meter weighting'),self.cal_weight,'Selecione a ponderação do nível medido. Em microfone aéreo o sinal de calibração recebe o mesmo filtro; o fator escalar é aplicado às trilhas A e Z. Não use dBC como dBZ.','Match the measured level weighting. For an air microphone, calibration audio receives the same filter; the scalar factor applies to A and Z tracks. Do not substitute dBC for dBZ.')
        self.cal_paths=[];self.cal_levels=[]
        for i in range(3):
            h=QHBoxLayout();path=QLineEdit();path.setReadOnly(True);path.setPlaceholderText(self.T('Opcional · escolher áudio','Optional · choose audio'))
            level=self.spin([65,80,90][i],20,140,.5,1,' dB');b=self.button('…','…',lambda checked=False,index=i:self.pick_calibration(index));b.setFixedWidth(34)
            h.addWidget(path,1);h.addWidget(b);h.addWidget(level)
            field=QWidget();field.setLayout(h);h.setContentsMargins(0,0,0,0)
            self.field(form,self.T(f'Ponto {i+1}',f'Point {i+1}'),field,'Grave uma emissão estável, com leitura simultânea do sonômetro. Selecione o trecho estável, sem silêncio ou saturação. Microfone aéreo aceita 1 a 3 pontos; contato exige 3 pontos com amplitude de pelo menos 10 dB.','Record a steady emission with simultaneous sound level meter reading. Select the steady segment, without silence or clipping. Air microphone accepts 1-3 points; contact requires 3 spanning at least 10 dB.')
            self.cal_paths.append(path);self.cal_levels.append(level)
            if i<len(cfg.calibration):path.setText(cfg.calibration[i]['path']);level.setValue(cfg.calibration[i]['level'])
        self.clear_cal=self.button('Limpar calibração','Clear calibration',self.clear_calibration);form.addRow('',self.clear_cal)
        self.dist_cal=self.spin(cfg.calibration_distance_m*100,1,1000,5,1,' cm')
        self.field(form,self.T('Distância boca-sonômetro','Mouth-to-meter distance'),self.dist_cal,'Distância da boca ao sonômetro durante a calibração. Em sensor de contato, não é a distância da pele ao sensor.','Mouth-to-meter distance during calibration. For a contact sensor, this is not the skin-to-sensor distance.')
        self.dist_target=self.spin(cfg.target_distance_m*100,1,1000,5,1,' cm')
        self.field(form,self.T('Distância de referência','Reference distance'),self.dist_target,'Distância para exibir SPL, assumindo campo livre: L2=L1+20log10(r1/r2). As equações biomecânicas usam internamente 50 cm; Dr usa o raio correspondente.','Distance for reported SPL under a free-field assumption: L2=L1+20log10(r1/r2). Biomechanical equations use 50 cm internally; Dr uses the corresponding radius.')
        cv.addWidget(group)
        group=QGroupBox(self.T('Detecção e medidas','Detection and measures'));form=QFormLayout(group);form.setSpacing(10)
        self.preset=self.combo([(self.T('Personalizado','Custom'),'custom'),(self.T('Fala · faixa ampla','Speech · wide range'),'speech'),(self.T('Canto · faixa ampla','Singing · wide range'),'singing')])
        self.preset.currentIndexChanged.connect(self.apply_preset)
        self.field(form,self.T('Predefinição de F0','F0 preset'),self.preset,'Atalhos editáveis: fala 60-500 Hz; canto 50-1200 Hz. Ajuste à voz real; a faixa não define gênero.','Editable shortcuts: speech 60-500 Hz; singing 50-1200 Hz. Adapt to the actual voice; pitch range does not define gender.')
        pair=QWidget();hh=QHBoxLayout(pair);hh.setContentsMargins(0,0,0,0)
        self.fmin=self.spin(cfg.f0_min,30,1999,5,0,' Hz');self.fmax=self.spin(cfg.f0_max,31,2000,10,0,' Hz');hh.addWidget(self.fmin);hh.addWidget(QLabel('—'));hh.addWidget(self.fmax)
        self.field(form,self.T('Faixa de F0: mín. / máx.','F0 range: min. / max.'),pair,'Limites da autocorrelação Praat. Limites incorretos podem gerar erros de oitava ou perder fonação. Confira o gráfico após analisar.','Praat autocorrelation bounds. Incorrect bounds can cause octave errors or missed voicing. Check the plot after analysis.')
        self.model=self.combo([(self.T('Média dos dois modelos','Mean of both models'),'average'),(self.T('Modelo masculino histórico','Historical male model'),'male'),(self.T('Modelo feminino histórico','Historical female model'),'female')],cfg.model)
        self.field(form,self.T('Modelo biomecânico','Biomechanical model'),self.model,'A escolha altera apenas Dd e De. São pressupostos anatômicos históricos, não determinação de identidade. A média combina as doses dos dois modelos. Registre a escolha para reproduzir a análise.','This choice only changes Dd and De. These are historical anatomical assumptions, not identity classification. The mean combines the doses from both models. Record the choice for reproducibility.')
        self.gate_fs=self.spin(cfg.gate_dbfs,-120,0,1,1,' dBFS')
        self.field(form,self.T('Limiar sem calibração','Uncalibrated gate'),self.gate_fs,'Quadros precisam de F0 detectada e nível digital acima deste limiar. Não elimina outras pessoas falando.','Frames require detected F0 and a digital level above this gate. This does not exclude other speakers.')
        self.gate_spl=self.spin(cfg.gate_spl,0,140,1,1,' dB')
        self.field(form,self.T('Limiar com calibração','Calibrated gate'),self.gate_spl,'Aplicado ao SPL A, ou Z se A não existir, na distância de referência. Ajuste ao ruído e à tarefa; não é limite de segurança.','Applied to SPL A, or Z if A is unavailable, at the reference distance. Adjust to noise and task; this is not a safety threshold.')
        self.trend=self.spin(cfg.window_s,5,3600,5,0,' s')
        self.field(form,self.T('Janela dos resumos','Summary window'),self.trend,'Janelas não sobrepostas para comparar a evolução. A última janela usa sua duração real; taxas são normalizadas pelo tempo representado.','Non-overlapping windows for tracking changes. The last window uses its actual duration; rates are normalized by represented time.')
        self.cpps=QCheckBox(self.T('Calcular CPPS e HNR','Compute CPPS and HNR'));self.cpps.setChecked(cfg.cpps)
        self.field(form,self.T('Qualidade vocal','Voice quality'),self.cpps,'Medidas complementares em janelas originais de 5 s. CPPS e HNR não são medidas específicas de fadiga. Desative para reduzir o tempo de processamento.','Complementary measures in original 5 s windows. CPPS and HNR are not specific measures of fatigue. Disable to reduce processing time.')
        cv.addWidget(group);cv.addStretch();scroll.setWidget(controls);split.addWidget(scroll);split.setSizes([420,850])
        row=QHBoxLayout();self.run_button=self.button('Analisar gravações','Analyze recordings',self.run_analysis,True)
        self.cancel_button=self.button('Cancelar','Cancel',self.cancel_job);self.cancel_button.setEnabled(False)
        self.progress=QProgressBar();self.progress.setValue(0)
        row.addWidget(self.run_button);row.addWidget(self.cancel_button);row.addWidget(self.progress,1);v.addLayout(row)
        self.analysis_status=self.label('Pronto. Os resultados serão salvos na pasta results da versão 2.0.','Ready. Results will be saved in the version 2.0 results folder.','muted');v.addWidget(self.analysis_status)
        return p

    def doses_page(self):
        p,v=self.page();v.addWidget(self.label('Doses vocais e medidas acústicas','Vocal doses and acoustic measures','heading'))
        self.quality_label=self.label('Analise ou abra uma sessão para ver os resultados.','Analyze or open a session to view results.','muted');v.addWidget(self.quality_label)
        row=QHBoxLayout();self.kpi_values={}
        for key in ['dt_s','dt_pct','vli_kcycles','dd_m','cpps_db']:
            c=self.card();cl=QVBoxLayout(c);cl.setContentsMargins(15,12,15,12);label,unit,explain=metric(key,self.language)
            cap,_=self.info(label,explain,explain);cl.addWidget(cap)
            num=QLabel('—');num.setStyleSheet('font-size:25px;font-weight:650;color:#1197A0;');cl.addWidget(num)
            cl.addWidget(QLabel(unit));row.addWidget(c,1);self.kpi_values[key]=num
        v.addLayout(row)
        range_row=QHBoxLayout();range_row.addWidget(self.label('Intervalo (segundos)','Interval (seconds)'))
        self.range_start=self.spin(0,0,1000000,1,2,' s');self.range_end=self.spin(0,0,1000000,1,2,' s')
        range_row.addWidget(self.range_start);range_row.addWidget(QLabel('→'));range_row.addWidget(self.range_end)
        self.interval_button=self.button('Aplicar intervalo','Apply interval',self.apply_interval);range_row.addWidget(self.interval_button)
        self.full_button=self.button('Gravação inteira','Whole recording',self.whole_recording);range_row.addWidget(self.full_button);range_row.addStretch();v.addLayout(range_row)
        self.range_note=self.label('Tabela: gravação inteira','Table: whole recording','muted');v.addWidget(self.range_note)
        self.metric_search=QLineEdit();self.metric_search.setPlaceholderText(self.T('Buscar medida ou unidade…','Search measure or unit…'));self.metric_search.textChanged.connect(self.filter_metrics);v.addWidget(self.metric_search)
        self.dose_table=self.table([self.T('Medida','Measure'),self.T('Valor','Value'),self.T('Unidade','Unit'),self.T('Interpretação / método','Interpretation / method')])
        self.dose_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
        self.dose_table.setColumnWidth(1,145);self.dose_table.setColumnWidth(2,105)
        self.dose_table.setSortingEnabled(True);self.dose_table.itemDoubleClicked.connect(self.metric_info);v.addWidget(self.dose_table,1)
        self.dose_table.horizontalHeader().setSortIndicator(-1,Qt.AscendingOrder)
        row=QHBoxLayout();row.addWidget(self.button('Copiar tabela','Copy table',self.copy_metrics));row.addWidget(self.button('Exportar tabela do intervalo','Export interval table',self.export_interval));row.addStretch()
        row.addWidget(self.label('Clique duas vezes para consultar a descrição da medida.','Double-click for the measure description.','muted'));v.addLayout(row)
        return p

    def charts_page(self):
        p,v=self.page();row=QHBoxLayout();row.addWidget(self.label('Gráficos das medidas vocais','Vocal measure plots','heading'));row.addStretch()
        labels=[self.T('Intensidade','Intensity'),'F0','CPPS',self.T('Ciclos acumulados','Accumulated cycles'),self.T('Fonação','Phonation'),self.T('Distribuição de F0','F0 distribution'),self.T('Distribuição de intensidade','Intensity distribution'),self.T('Distribuição de CPPS','CPPS distribution'),'HNR',self.T('Envelope RMS','RMS envelope'),self.T('Dose de distância','Distance dose'),self.T('Dose de dissipação','Dissipation dose'),self.T('Energia radiada','Radiated energy')]
        self.plot_kind=self.combo([(self.T('Painel conjunto','Combined dashboard'),None)]+list(zip(labels,KINDS)))
        self.plot_kind.currentIndexChanged.connect(self.render_chart);row.addWidget(self.plot_kind)
        row.addWidget(self.button('Abrir separado','Open separately',self.separate_plot));v.addLayout(row)
        self.chart=PlotWidget();v.addWidget(self.chart,1)
        v.addWidget(self.label('Cinza: pausas sem fonação detectada (≥0,5 s). A média só aparece na fonação e em janelas com ≥5% e ≥0,5 s de fonação. Os dados originais e as doses são preservados.','Gray: pauses without detected voicing (≥0.5 s). Means appear only during voicing, in windows with ≥5% and ≥0.5 s voicing. Original data and doses are preserved.','muted'))
        return p

    def compare_page(self):
        p,v=self.page();v.addWidget(self.label('Comparação de gravações','Recording comparison','heading'))
        row=QHBoxLayout();self.compare_checks=QTableWidget(0,3);self.compare_checks.setHorizontalHeaderLabels([self.T('Usar','Use'),self.T('Gravação','Recording'),self.T('Duração','Duration')]);self.compare_checks.verticalHeader().hide();self.compare_checks.setMaximumHeight(155)
        self.compare_checks.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.compare_checks.setColumnWidth(0,55)
        self.compare_checks.setEditTriggers(QAbstractItemView.NoEditTriggers);row.addWidget(self.compare_checks,1)
        options=QVBoxLayout();self.relative=QCheckBox(self.T('Eixo de tempo relativo (%)','Relative time axis (%)'));options.addWidget(self.relative)
        options.addWidget(self.button('Atualizar comparação','Update comparison',self.update_comparison,True))
        options.addWidget(self.button('Ampliar gráfico','Enlarge chart',self.separate_comparison))
        options.addWidget(self.button('Exportar comparação','Export comparison',self.export_comparison));options.addStretch();row.addLayout(options);v.addLayout(row)
        self.compare_note=self.label('Escolha pelo menos duas sessões. A primeira selecionada é a referência.','Choose at least two sessions. The first selected session is the reference.','muted');v.addWidget(self.compare_note)
        self.compare_table=self.table([self.T('Medida / unidade','Measure / unit')]);self.compare_table.setMaximumHeight(220);v.addWidget(self.compare_table)
        self.compare_plot=PlotWidget();v.addWidget(self.compare_plot,1);return p

    def diary_page(self):
        p,v=self.page();v.addWidget(self.label('Autorrelato de esforço, fadiga e desconforto','Self-reported effort, fatigue and discomfort','heading'))
        v.addWidget(self.label('Registro numérico descritivo de 0 a 10: 0 = nenhum; 10 = máximo imaginável. Não é VFI nem questionário validado. Relacione as avaliações às tarefas e aos momentos de coleta.','Descriptive numerical ratings from 0 to 10: 0 = none; 10 = maximum imaginable. This is not the VFI or a validated questionnaire. Link ratings to tasks and collection times.','muted'))
        form=QFormLayout();self.diary_time=QLineEdit();self.diary_phase=self.combo([(self.T('Antes da tarefa','Before task'),'before'),(self.T('Após a tarefa','After task'),'after'),(self.T('Acompanhamento / recuperação','Follow-up / recovery'),'followup')])
        self.field(form,self.T('Data/hora com fuso','Date/time with timezone'),self.diary_time,'Formato ISO 8601, por exemplo 2026-11-15T14:30:00-03:00. Pode registrar avaliações realizadas antes ou depois da gravação.','ISO 8601, for example 2026-11-15T14:30:00-03:00. You can enter ratings collected before or after the recording.')
        self.field(form,self.T('Momento','Phase'),self.diary_phase,'Identifica se a avaliação ocorreu antes, depois ou no acompanhamento. Não implica uma trajetória de recuperação calculada.','Identify baseline, post-task or follow-up. This does not imply a calculated recovery trajectory.')
        self.diary_ratings={}
        for key,pt,en in [('effort','Esforço percebido','Perceived effort'),('fatigue','Fadiga percebida','Perceived fatigue'),('discomfort','Desconforto percebido','Perceived discomfort')]:
            sp=self.spin(0,0,10,.5,1)
            self.field(form,self.T(pt,en),sp,'Registro autodeclarado independente. Zero = nenhum; dez = máximo imaginável. Não é calculado a partir do áudio.','Independent self-report. Zero = none; ten = maximum imaginable. Not calculated from the audio.')
            self.diary_ratings[key]=sp
        self.diary_text=QLineEdit();self.field(form,self.T('Contexto / observações','Context / notes'),self.diary_text,'Anote atividade, ambiente e condições de coleta para interpretar as mudanças.','Record activity, environment and collection conditions to interpret changes.')
        v.addLayout(form);row=QHBoxLayout();self.diary_add=self.button('Adicionar ao diário da sessão','Add to session diary',self.add_diary,True);row.addWidget(self.diary_add)
        row.addWidget(self.button('Excluir registro selecionado','Delete selected entry',self.remove_diary));row.addWidget(self.button('Exportar diário CSV','Export diary CSV',self.export_diary));row.addStretch();v.addLayout(row)
        self.diary_table=self.table([self.T('Data/hora','Date/time'),self.T('Momento','Phase'),self.T('Esforço','Effort'),self.T('Fadiga','Fatigue'),self.T('Desconforto','Discomfort'),self.T('Observações','Notes')]);v.addWidget(self.diary_table,1)
        self.diary_plot=PlotWidget();self.diary_plot.setMaximumHeight(250);v.addWidget(self.diary_plot);return p

    def settings_page(self):
        p,v=self.page();v.addWidget(self.label('Configurações','Settings','heading'))
        group=QGroupBox(self.T('Preferências','Preferences'));form=QFormLayout(group)
        self.language_combo=self.combo([('Português brasileiro','pt_BR'),('English','en_US')],self.language)
        self.field(form,self.T('Idioma','Language'),self.language_combo,'A interface, os textos de ajuda e as novas exportações usam o idioma selecionado. As chaves técnicas de CSV/JSON permanecem estáveis.','The interface, help and new exports use the selected language. Technical CSV/JSON keys remain stable.')
        self.theme_combo=self.combo([(self.T('Claro','Light'),'light'),(self.T('Escuro','Dark'),'dark')],self.theme)
        self.field(form,self.T('Tema','Theme'),self.theme_combo,'Preferência de aparência. Gráficos exportados mantêm fundo branco para publicação.','Appearance preference. Exported figures retain a white background for publication.')
        self.tutorial_check=QCheckBox(self.T('Mostrar botões (i) e dicas de campos','Show (i) buttons and field tips'));self.tutorial_check.setChecked(self.tutorials)
        self.field(form,self.T('Tutoriais contextuais','Contextual tutorials'),self.tutorial_check,'Desabilita os botões (i) e as dicas de campos. O guia e as descrições da tabela continuam disponíveis.','Disable (i) buttons and field tips. The guide and table descriptions remain available.')
        self.separate_check=QCheckBox(self.T('Exportar painel conjunto e gráficos separados','Export overview and separate plots'));self.separate_check.setChecked(self.settings.value('separate',True,type=bool))
        self.field(form,self.T('Gráficos na exportação','Export figures'),self.separate_check,'PNG em alta resolução e SVG vetorial. A opção controla a exportação; as janelas separadas sempre estão disponíveis.','High-resolution PNG and vector SVG. This controls export; separate plot windows are always available.')
        v.addWidget(group);row=QHBoxLayout();self.apply_settings_button=self.button('Aplicar preferências','Apply preferences',self.apply_settings,True);row.addWidget(self.apply_settings_button)
        row.addWidget(self.button('Abrir pasta de resultados','Open results folder',self.open_results));row.addStretch();v.addLayout(row)
        about=QTextBrowser();about.setOpenExternalLinks(True)
        about.setHtml(self.about_html());v.addWidget(about,1);return p

    def about_html(self):
        return '<h2>VoxDose 2.0</h2><p><b>'+AUTHOR+'</b><br>'+AFFILIATION+'</p><p>'+self.T(
            'Desenvolvimento e modernização da versão 2.0: interface, arquitetura, processamento em blocos, comparações, gráficos, diário, exportações e documentação por Tiago Lima Bicalho Cruz.',
            'Version 2.0 development and modernization: interface, architecture, streaming processing, comparisons, figures, diary, exports and documentation by Tiago Lima Bicalho Cruz.')+'</p><p>'+self.T(
            'Adaptação dos códigos originais de dosimetria em MATLAB de Pasquale Bottalico. Fundamentação das doses: Titze, Švec e Popolo (2003). As correções numéricas da versão 2.0 estão descritas em METHODS.md.',
            'Adapted from original MATLAB dosimetry code by Pasquale Bottalico. Dose framework: Titze, Švec and Popolo (2003). Version 2.0 numerical corrections are described in METHODS.md.')+'</p><p><a href="https://doi.org/10.1044/2023_JSLHR-23-00060">Bottalico &amp; Nudelman (2023)</a> · <a href="https://doi.org/10.1007/s00405-025-09970-0">Castillo-Allendes et al. / Hunter (2026)</a></p><p>'+self.T(
            'Ferramenta de pesquisa: as medidas descrevem exposição e características acústicas; não fornecem diagnóstico ou limite universal de fadiga. Processamento local, sem envio de áudio para a nuvem.',
            'Research tool: measures describe exposure and acoustic characteristics; they do not provide a diagnosis or universal fatigue threshold. Local processing, without cloud audio uploads.')+'</p>'

    def help_page(self):
        p,v=self.page();v.addWidget(self.label('Manual e métodos','Manual and methods','heading'))
        row=QHBoxLayout();row.addWidget(self.button('Manual ilustrado em português','Illustrated Portuguese manual',lambda:self.open_manual('pt_BR')))
        row.addWidget(self.button('Manual ilustrado em inglês','Illustrated English manual',lambda:self.open_manual('en_US')))
        row.addWidget(self.button('Relatório de desenvolvimento','Development report',self.open_report));row.addStretch();v.addLayout(row)
        browser=QTextBrowser();browser.setOpenExternalLinks(True)
        browser.setHtml(self.T('''<h2>1. Prepare a gravação</h2><p>Use WAV ou FLAC preferencialmente. Escolha o canal correto e identifique participante, tarefa e montagem. Arquivos MP3 dependem do suporte da biblioteca de áudio local.</p>
<h2>2. Calibre quando precisar de SPL e doses modeladas</h2><p>Use emissões estáveis gravadas com o mesmo ganho do monitoramento e leitura simultânea do sonômetro. Informe ponderação A ou Z e distância boca-sonômetro. Sem calibração: dBFS, Dt e Dc continuam disponíveis; Dd, De e Dr ficam indisponíveis.</p>
<h2>3. Confira a detecção</h2><p>Ajuste F0 mínima/máxima e limiares ao sinal. A análise exige F0 detectada e nível acima do limiar. Não separa automaticamente a voz de outras pessoas em microfones aéreos. Cancelamento ocorre entre blocos de processamento.</p>
<h2>4. Leia as doses e os gráficos</h2><p>Dt representa duração de fonação; Dc ciclos; VLI milhares de ciclos. Dd e De são estimativas biomecânicas. De é expressa em J/m³; Dr em J. O CPPS usa janelas originais de 5 s com pelo menos 20% de fonação, sem concatenar segmentos. HNR é exploratório.</p>
<h2>5. Compare e registre a percepção</h2><p>Marque pelo menos duas sessões na aba Comparação. Use taxas por hora para durações diferentes. Diferenças diretas são bloqueadas quando participante, tarefa, dispositivo ou método não são comparáveis. O eixo relativo alinha o início e o fim de cada arquivo, sem alinhar eventos reais.</p>
<h2>6. Exporte e retome</h2><p>Uma análise concluída salva uma sessão .voxdose, CSV compactado por quadro, resumo Excel e metadados. Use Exportar resultados para obter também os gráficos PNG e SVG. Ctrl+O adiciona áudios; Ctrl+S salva a sessão ativa; F1 abre este guia.</p>
<h2>Contato e acelerometria</h2><p>O modo experimental registra o tipo de sensor. Sem calibração própria, oferece apenas níveis digitais e medidas de tempo/ciclos/periodicidade. Estimar SPL exige três referências simultâneas e acoplamento estável. Referências A não permitem inferir SPL Z do contato; nesse caso Dd, De e Dr permanecem indisponíveis. Valores de CPPS/HNR não devem ser trocados entre sensores como se fossem equivalentes.</p>''',
'''<h2>1. Prepare your recording</h2><p>Prefer WAV or FLAC. Select the correct channel and identify participant, task and setup. MP3 depends on the local audio library.</p>
<h2>2. Calibrate for SPL and modeled doses</h2><p>Use steady emissions recorded at the monitoring gain with simultaneous sound level meter readings. Enter A or Z weighting and mouth-to-meter distance. Without calibration: dBFS, Dt and Dc remain available; Dd, De and Dr are unavailable.</p>
<h2>3. Check detection</h2><p>Adapt F0 bounds and gates to the signal. Analysis requires detected F0 and a level above the gate. Air microphones cannot automatically distinguish the participant from other speakers. Cancellation occurs between processing blocks.</p>
<h2>4. Read doses and plots</h2><p>Dt is phonation duration; Dc cycles; VLI thousand cycles. Dd and De are biomechanical estimates. De is reported in J/m³; Dr in J. CPPS uses original 5 s windows with at least 20% voicing, without concatenating segments. HNR is exploratory.</p>
<h2>5. Compare and record perceptions</h2><p>Select at least two sessions in Comparison. Use per-hour rates for different durations. Direct differences are withheld when participant, task, device or method are not comparable. Relative time aligns file start and end, not actual events.</p>
<h2>6. Export and resume</h2><p>A completed analysis saves a .voxdose session, compressed frame CSV, summary Excel and metadata. Export results also generates PNG and SVG figures. Ctrl+O adds audio; Ctrl+S saves the active session; F1 opens this guide.</p>
<h2>Contact and accelerometry</h2><p>Experimental mode records the sensor type. Without a dedicated calibration, only digital levels and time/cycle/periodicity measures are available. Estimating SPL requires three simultaneous reference levels and stable coupling. A-weighted contact references cannot infer contact SPL Z; Dd, De and Dr remain unavailable. CPPS/HNR values cannot be interchanged between sensors as equivalent measurements.</p>''')+self.about_html())
        v.addWidget(browser,1);return p

    def read_config(self):
        return Config(sensor=self.sensor.currentData(),channel=self.channel.value()-1,f0_min=self.fmin.value(),f0_max=self.fmax.value(),
            model=self.model.currentData(),calibration=[{'path':p.text(),'level':l.value()} for p,l in zip(self.cal_paths,self.cal_levels) if p.text()],
            calibration_weighting=self.cal_weight.currentData(),calibration_distance_m=self.dist_cal.value()/100,
            target_distance_m=self.dist_target.value()/100,gate_dbfs=self.gate_fs.value(),gate_spl=self.gate_spl.value(),
            window_s=self.trend.value(),cpps=self.cpps.isChecked(),subject=self.subject.text().strip(),task=self.task.text().strip(),
            device=self.device.text().strip(),notes=self.notes.text().strip())

    def apply_preset(self):
        selected=self.preset.currentData()
        if selected in {'speech','singing'}:
            lo,hi=(60,500) if selected=='speech' else (50,1200)
            self.fmin.setValue(lo);self.fmax.setValue(hi)

    def pick_calibration(self,index):
        path,_=QFileDialog.getOpenFileName(self,self.T('Selecionar calibração','Select calibration'),str(BASE.parent/'Python'),'Audio (*.wav *.WAV *.flac *.FLAC *.mp3 *.MP3 *.ogg *.aiff)')
        if path:self.cal_paths[index].setText(path)
    def clear_calibration(self):
        for p in self.cal_paths:p.clear()

    def add_files(self):
        files,_=QFileDialog.getOpenFileNames(self,self.T('Selecionar gravações','Select recordings'),str(BASE.parent/'Python'),'Audio (*.wav *.WAV *.flac *.FLAC *.mp3 *.MP3 *.ogg *.aiff)')
        self.add_paths(files)
    def add_paths(self,paths):
        if self.job and self.job.isRunning():return
        errors=[]
        for p in paths:
            p=str(Path(p).resolve())
            if p in self.files:continue
            try:sf.info(p);self.files.append(p)
            except Exception as e:errors.append(Path(p).name+': '+str(e))
        self.refresh_queue();self.update_enabled()
        if errors:QMessageBox.warning(self,self.T('Áudios não carregados','Audio not loaded'),'\n'.join(errors))
    def refresh_queue(self):
        self.queue.setRowCount(len(self.files))
        for row,p in enumerate(self.files):
            info=sf.info(p)
            for col,val in enumerate([Path(p).name,f'{info.duration/60:.2f} min',str(info.channels)]):
                item=QTableWidgetItem(val);item.setToolTip(p);self.queue.setItem(row,col,item)
    def remove_files(self):
        for row in sorted({i.row() for i in self.queue.selectedIndexes()},reverse=True):self.files.pop(row)
        self.refresh_queue();self.update_enabled()
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
    def dropEvent(self,event):
        self.add_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]);event.acceptProposedAction()

    def start_job(self,fn):
        if self.job and self.job.isRunning():return
        self.job=Job(fn,self);self.job.progress.connect(self.on_progress);self.job.item.connect(self.on_item)
        self.job.error.connect(self.on_error);self.job.note.connect(self.on_note);self.job.finished.connect(self.job_finished)
        self.progress.setValue(0);self.job.start();self.update_enabled()
    def run_analysis(self):
        try:cfg=self.read_config();cfg.validate()
        except Exception as e:self.on_error(str(e));return
        paths=list(self.files);language=self.language
        if not paths:return
        def work(job):
            for i,path in enumerate(paths):
                if job.cancel.is_set():raise Cancelled()
                def prog(value,name):job.progress.emit(int(100*(i+value/100)/len(paths)),name)
                try:
                    r=analyze(path,copy.deepcopy(cfg),prog,job.cancel)
                    if job.cancel.is_set():raise Cancelled()
                    folder=new_output_folder(r);save_session(r,folder/'session.voxdose');export_tables(r,folder,language)
                    job.item.emit(('result',r,str(folder)))
                except Cancelled:raise
                except Exception as e:
                    logging.exception('Analysis failed for %s',path);job.error.emit(Path(path).name+'\n'+str(e))
            job.note.emit(self.T('Lote finalizado. Confira os resultados e as mensagens de qualidade.','Batch finished. Review results and quality messages.'))
        self.start_job(work)
    def cancel_job(self):
        if self.job:self.job.cancel.set();self.cancel_button.setEnabled(False);self.analysis_status.setText(self.T('Cancelando após o bloco atual…','Cancelling after the current block…'))
    @Slot(int,str)
    def on_progress(self,value,name):
        self.progress.setValue(value);self.analysis_status.setText(self.T('Processando: ','Processing: ')+name)
    @Slot(object)
    def on_item(self,item):
        if item[0]=='result':
            _,r,folder=item;self.results.append(r);self.result_paths[id(r)]=folder
            self.selector.addItem(r.label,len(self.results)-1);self.selector.setCurrentIndex(len(self.results));self.populate_comparison()
            self.analysis_status.setText(self.T('Salvo em: ','Saved to: ')+folder)
        elif item[0]=='opened':
            for r,path in item[1]:
                self.results.append(r);self.result_paths[id(r)]=str(Path(path).parent)
                self.selector.addItem(r.label,len(self.results)-1)
            self.selector.setCurrentIndex(len(self.results));self.populate_comparison()
        elif item[0]=='exported':
            self.analysis_status.setText(self.T('Exportação concluída: ','Export complete: ')+item[1]);self.statusBar().showMessage(self.analysis_status.text(),15000)
    @Slot(str)
    def on_note(self,message):self.analysis_status.setText(message);self.statusBar().showMessage(message,15000)
    @Slot(str)
    def on_error(self,message):
        self.analysis_status.setText(self.T('Falha: ','Failed: ')+message.replace('\n',' · '));self.statusBar().showMessage(self.analysis_status.text(),30000)
        QMessageBox.warning(self,self.T('Não foi possível concluir a operação','Operation could not be completed'),message)
    @Slot()
    def job_finished(self):
        self.update_enabled()
        if self.results:self.tabs.setCurrentIndex(1)
    def update_enabled(self):
        busy=bool(self.job and self.job.isRunning());has=self.current_result() is not None
        self.run_button.setEnabled(bool(self.files) and not busy);self.cancel_button.setEnabled(busy)
        for b in [self.add_button,self.remove_button,self.clear_cal,self.open_button,self.apply_settings_button]:b.setEnabled(not busy)
        self.save_button.setEnabled(has and not busy);self.export_button.setEnabled(has and not busy)
        self.diary_add.setEnabled(has and not busy);self.interval_button.setEnabled(has);self.full_button.setEnabled(has)

    def current_result(self):
        return self.results[self.selected_index] if 0<=self.selected_index<len(self.results) else None
    def select_result(self,index):
        self.selected_index=self.selector.currentData() if index>=0 else -1;self.refresh_results();self.update_enabled()
    def refresh_results(self):
        r=self.current_result()
        if r:
            self.range_start.setValue(0);self.range_end.setValue(r.metadata['duration_s'])
            self.show_summary(r.summary)
            flags=[WARNINGS.get(w,(w,w))[0 if self.language=='pt_BR' else 1] for w in r.warnings]
            self.quality_label.setText(('  •  '.join(flags) if flags else self.T('Análise concluída.','Analysis complete.'))+'\n'+level_unit(r)+'  ·  '+self.T('Janela: ','Window: ')+str(r.metadata['config']['window_s'])+' s')
            self.render_chart();self.refresh_diary()
        self.populate_comparison()
    def show_summary(self,summary):
        self.display_summary=summary
        for key,num in self.kpi_values.items():num.setText(fmt(summary.get(key),self.language,2))
        self.dose_table.setSortingEnabled(False);self.dose_table.setRowCount(0)
        for key in METRICS:
            if key not in summary:continue
            name,unit,explain=metric(key,self.language);row=self.dose_table.rowCount();self.dose_table.insertRow(row)
            value=summary[key]
            for col,text in enumerate([name,fmt(value,self.language),unit,explain]):
                item=SortItem(text);item.setData(Qt.UserRole,(-float('inf') if value is None else float(value)) if col==1 else key)
                item.setData(Qt.UserRole+1,key);item.setToolTip(explain if self.tutorials else '')
                if col==1:item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                if value is None:item.setForeground(QColor('#8496A5'))
                self.dose_table.setItem(row,col,item)
        self.dose_table.setSortingEnabled(True);self.filter_metrics()
    def filter_metrics(self):
        search=self.metric_search.text().casefold()
        for row in range(self.dose_table.rowCount()):
            self.dose_table.setRowHidden(row,search not in ' '.join(self.dose_table.item(row,c).text().casefold() for c in [0,2,3]))
    def metric_info(self,item):
        name,unit,explain=metric(item.data(Qt.UserRole+1),self.language);QMessageBox.information(self,name,explain+'\n\n'+unit)
    def apply_interval(self):
        r=self.current_result()
        if not r:return
        lo=self.range_start.value();hi=self.range_end.value()
        if not 0<=lo<hi<=r.metadata['duration_s']+.01:self.on_error(self.T('Informe 0 ≤ início < fim ≤ duração.','Enter 0 ≤ start < end ≤ duration.'));return
        self.show_summary(summarize(r.frames,r.acoustic,Config(**r.metadata['config']),lo,hi))
        self.range_note.setText(self.T('Tabela do intervalo: ','Interval table: ')+f'{lo:.2f} - {hi:.2f} s · '+self.T('CPPS/HNR usam as janelas de 5 s que se sobrepõem ao intervalo.','CPPS/HNR use the 5 s windows overlapping this interval.'))
    def whole_recording(self):
        r=self.current_result()
        if r:self.range_start.setValue(0);self.range_end.setValue(r.metadata['duration_s']);self.show_summary(r.summary);self.range_note.setText(self.T('Tabela: gravação inteira','Table: whole recording'))
    def copy_metrics(self):
        rows=['\t'.join(self.dose_table.horizontalHeaderItem(c).text() for c in range(4))]
        rows += ['\t'.join(self.dose_table.item(i,c).text() for c in range(4)) for i in range(self.dose_table.rowCount()) if not self.dose_table.isRowHidden(i)]
        QApplication.clipboard().setText('\n'.join(rows));self.statusBar().showMessage(self.T('Tabela copiada.','Table copied.'),4000)
    def export_interval(self):
        r=self.current_result()
        if not r:return
        folder=Path(self.result_paths.get(id(r),str(OUTPUT)));folder.mkdir(parents=True,exist_ok=True)
        rows=[{'id':k,'measure':metric(k,self.language)[0],'value':v,'unit':metric(k,self.language)[1]} for k,v in self.display_summary.items() if k in METRICS]
        path=folder/f'interval_{self.range_start.value():.2f}_{self.range_end.value():.2f}.csv'
        pd.DataFrame(rows).to_csv(path,index=False,encoding='utf-8-sig');self.statusBar().showMessage(str(path),15000)
    def render_chart(self):
        if hasattr(self,'chart') and self.current_result():self.chart.set_figure(dashboard(self.current_result(),self.language,self.plot_kind.currentData()))
    def separate_plot(self):
        r=self.current_result()
        if not r:return
        dialog=QDialog(self);dialog.setWindowTitle('VoxDose 2.0 · '+r.label);dialog.resize(1150,760)
        v=QVBoxLayout(dialog);plot=PlotWidget();plot.set_figure(dashboard(r,self.language,self.plot_kind.currentData()));v.addWidget(plot)
        self.plot_dialogs.append(dialog);dialog.finished.connect(lambda:self.plot_dialogs.remove(dialog) if dialog in self.plot_dialogs else None);dialog.show()
    def tab_changed(self,index):
        if index==2:self.render_chart()
        elif index==4:self.refresh_diary()

    def populate_comparison(self):
        if not hasattr(self,'compare_checks'):return
        previous_count=self.compare_checks.rowCount()
        checked=set()
        for row in range(self.compare_checks.rowCount()):
            if self.compare_checks.item(row,0).checkState()==Qt.Checked:checked.add(row)
        self.compare_checks.setRowCount(len(self.results))
        for row,r in enumerate(self.results):
            check=QTableWidgetItem();check.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
            check.setCheckState(Qt.Checked if row in checked or (row>=previous_count and row<2) else Qt.Unchecked)
            self.compare_checks.setItem(row,0,check);self.compare_checks.setItem(row,1,QTableWidgetItem(r.label));self.compare_checks.setItem(row,2,QTableWidgetItem(f'{r.metadata["duration_s"]/60:.2f} min'))
    def comparison_results(self):
        return [r for i,r in enumerate(self.results) if self.compare_checks.item(i,0).checkState()==Qt.Checked]
    def comparison_frame(self,chosen):
        keys=['duration_s','dt_s','dt_pct','vli_kcycles','dc_cycles_per_hour','dd_m','dd_m_per_hour','de_j_m3_per_hour','dr_j_per_hour','f0_mean','spl_z_mean','cpps_db','long_pause_count']
        data={}
        for r in chosen:
            name=r.label
            if name in data:name+=f' [{len(data)+1}]'
            data[name]=[r.summary.get(k) for k in keys]
        df=pd.DataFrame(data,index=keys);return df
    def update_comparison(self):
        chosen=self.comparison_results()
        if len(chosen)<2:self.compare_note.setText(self.T('Selecione pelo menos duas sessões.','Select at least two sessions.'));return
        df=self.comparison_frame(chosen);self.compare_table.setColumnCount(1+len(chosen)*2)
        headers=[self.T('Medida / unidade','Measure / unit')]
        reasons=[[]]+[compatibility(chosen[0],r) for r in chosen[1:]]
        for i,name in enumerate(df.columns):headers.extend([name,self.T('Δ vs. referência','Δ vs. reference')])
        self.compare_table.setHorizontalHeaderLabels(headers);self.compare_table.setRowCount(len(df))
        for row,key in enumerate(df.index):
            name,unit,_=metric(key,self.language);self.compare_table.setItem(row,0,QTableWidgetItem(name+' ('+unit+')'))
            base=chosen[0].summary.get(key)
            for i,r in enumerate(chosen):
                val=r.summary.get(key);delta='—'
                if i and not reasons[i] and val is not None and base is not None:delta=fmt(val-base,self.language)
                self.compare_table.setItem(row,1+i*2,QTableWidgetItem(fmt(val,self.language)))
                item=QTableWidgetItem(delta)
                if reasons[i]:item.setToolTip(', '.join(reasons[i]))
                self.compare_table.setItem(row,2+i*2,item)
        self.compare_table.resizeColumnsToContents()
        reason_labels={
            'subject':self.T('participante ausente ou diferente','missing or different participant'),
            'task':self.T('tarefa ausente ou diferente','missing or different task'),
            'device':self.T('dispositivo/montagem ausente ou diferente','missing or different device/setup'),
            'sensor':self.T('tipo de sensor diferente','different sensor type'),
            'model':self.T('modelo biomecânico diferente','different biomechanical model'),
            'f0_min':self.T('F0 mínima diferente','different minimum F0'),
            'f0_max':self.T('F0 máxima diferente','different maximum F0'),
            'gate_dbfs':self.T('limiar digital diferente','different digital gate'),
            'gate_spl':self.T('limiar de SPL diferente','different SPL gate'),
            'cpps':self.T('opção CPPS diferente','different CPPS setting'),
            'channel':self.T('canal diferente','different channel'),
            'target_distance_m':self.T('distância de referência diferente','different reference distance'),
            'calibration':self.T('tipo de calibração diferente','different calibration type'),
            'calibration_weighting':self.T('ponderação da calibração diferente','different calibration weighting'),
            'model_version':self.T('versão do método diferente','different method version'),
            'contact_experimental':self.T('sensor de contato experimental','experimental contact sensor')}
        issues=[' · '.join(reason_labels.get(k,k) for k in r) for r in reasons[1:] if r]
        self.compare_note.setText(self.T('Diferenças diretas indisponíveis: ','Direct differences unavailable: ')+ '; '.join(issues) if issues else self.T('Métodos e contexto compatíveis. Para durações diferentes, priorize taxas por hora. Δ é uma diferença descritiva, sem teste de significância.','Methods and context are compatible. For different durations, prioritize per-hour rates. Δ is a descriptive difference, without a significance test.'))
        self.compare_plot.set_figure(comparison(chosen,self.language,self.relative.isChecked()))
    def export_comparison(self):
        chosen=self.comparison_results()
        if len(chosen)<2:return
        self.update_comparison();language=self.language;relative=self.relative.isChecked()
        chosen=copy.deepcopy(chosen)
        def work(job):
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            folder=OUTPUT/('comparison_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'));folder.mkdir(parents=True)
            df=self.comparison_frame(chosen);df.to_csv(folder/'comparison.csv',encoding='utf-8-sig',index_label='metric_id')
            fig=comparison(chosen,language,relative);FigureCanvasAgg(fig);fig.savefig(folder/'comparison.png',dpi=180);fig.savefig(folder/'comparison.svg');fig.clear()
            (folder/'provenance.json').write_text(json_text({'reference':chosen[0].metadata,'sessions':[r.metadata for r in chosen],
                'compatibility_reasons':[compatibility(chosen[0],r) for r in chosen[1:]],'relative_time':relative}),encoding='utf-8')
            job.item.emit(('exported',str(folder)))
        self.start_job(work)

    def separate_comparison(self):
        chosen=self.comparison_results()
        if len(chosen)<2:return
        dialog=QDialog(self);dialog.setWindowTitle(self.T('VoxDose 2.0 · Comparação','VoxDose 2.0 · Comparison'));dialog.resize(1200,830)
        v=QVBoxLayout(dialog);plot=PlotWidget();plot.set_figure(comparison(chosen,self.language,self.relative.isChecked()));v.addWidget(plot)
        self.plot_dialogs.append(dialog);dialog.finished.connect(lambda:self.plot_dialogs.remove(dialog) if dialog in self.plot_dialogs else None);dialog.show()

    def refresh_diary(self):
        if not hasattr(self,'diary_table'):return
        r=self.current_result();entries=r.metadata.get('diary',[]) if r else []
        self.diary_time.setText(datetime.now().astimezone().isoformat(timespec='seconds'))
        self.diary_table.setRowCount(len(entries))
        phases={'before':self.T('Antes','Before'),'after':self.T('Após','After'),'followup':self.T('Acompanhamento','Follow-up')}
        for i,e in enumerate(entries):
            vals=[e['timestamp'],phases.get(e['phase'],e['phase']),e['effort'],e['fatigue'],e['discomfort'],e['notes']]
            for j,val in enumerate(vals):self.diary_table.setItem(i,j,QTableWidgetItem(str(val)))
        self.diary_table.resizeColumnsToContents()
        fig=Figure(figsize=(10,2.2),facecolor='white',layout='constrained');ax=fig.subplots()
        from .plots import decorate
        if entries:
            dates=[datetime.fromisoformat(e['timestamp']) for e in entries]
            origin=min(dates);xx=[(d-origin).total_seconds()/3600 for d in dates];order=np.argsort(xx)
            for color,(key,pt,en) in zip(PALETTE,[('effort','Esforço','Effort'),('fatigue','Fadiga','Fatigue'),('discomfort','Desconforto','Discomfort')]):
                ax.plot(np.array(xx)[order],np.array([e[key] for e in entries])[order],marker='o',color=color,label=self.T(pt,en))
            ax.legend(frameon=False,fontsize=8);ax.set_xlabel(self.T('Horas desde o primeiro registro','Hours since first entry'))
        else:ax.text(.5,.5,self.T('As avaliações aparecerão aqui.','Your ratings will appear here.'),ha='center',transform=ax.transAxes,color='#7C8B99')
        ax.set_ylim(-.3,10.3);ax.set_ylabel('0–10');decorate(ax);self.diary_plot.set_figure(fig)
    def add_diary(self):
        r=self.current_result()
        if not r:return
        try:
            dt=datetime.fromisoformat(self.diary_time.text())
            if dt.tzinfo is None:raise ValueError(self.T('Informe o fuso, por exemplo -03:00.','Include timezone, e.g. -03:00.'))
        except ValueError as e:self.on_error(str(e));return
        entry={'timestamp':dt.isoformat(),'phase':self.diary_phase.currentData(),'notes':self.diary_text.text(),**{key:sp.value() for key,sp in self.diary_ratings.items()}}
        r.metadata.setdefault('diary',[]).append(entry);self.autosave_current();self.refresh_diary()
    def remove_diary(self):
        r=self.current_result()
        if not r:return
        for row in sorted({i.row() for i in self.diary_table.selectedIndexes()},reverse=True):r.metadata.get('diary',[]).pop(row)
        self.autosave_current();self.refresh_diary()
    def export_diary(self):
        r=self.current_result()
        if not r:return
        folder=Path(self.result_paths.get(id(r),str(OUTPUT)));folder.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(r.metadata.get('diary',[])).to_csv(folder/'diary.csv',index=False,encoding='utf-8-sig');self.statusBar().showMessage(str(folder/'diary.csv'),15000)

    def autosave_current(self):
        r=self.current_result()
        if not r:return
        folder=Path(self.result_paths.get(id(r),str(new_output_folder(r)) if id(r) not in self.result_paths else self.result_paths[id(r)]))
        self.result_paths[id(r)]=str(folder);save_session(r,folder/'session.voxdose')
    def save_current(self):
        if not self.current_result() or (self.job and self.job.isRunning()):return
        path,_=QFileDialog.getSaveFileName(self,self.T('Salvar sessão','Save session'),str(OUTPUT/(self.current_result().label+'.voxdose')),'VoxDose session (*.voxdose)')
        if path:
            if not path.lower().endswith('.voxdose'):path+='.voxdose'
            try:save_session(self.current_result(),Path(path));self.statusBar().showMessage(path,15000)
            except Exception as e:self.on_error(str(e))
    def open_session(self):
        if self.job and self.job.isRunning():return
        paths,_=QFileDialog.getOpenFileNames(self,self.T('Abrir sessões','Open sessions'),str(OUTPUT),'VoxDose session (*.voxdose)')
        if not paths:return
        def work(job):
            out=[]
            for p in paths:
                if job.cancel.is_set():raise Cancelled()
                out.append((load_session(Path(p)),p))
            job.item.emit(('opened',out))
        self.start_job(work)
    def export_current(self):
        r=self.current_result()
        if not r or (self.job and self.job.isRunning()):return
        r=copy.deepcopy(r);language=self.language;separate=self.settings.value('separate',True,type=bool)
        def work(job):
            folder=new_output_folder(r);save_session(r,folder/'session.voxdose');job.progress.emit(10,r.label)
            export_tables(r,folder,language);job.progress.emit(30,r.label)
            if job.cancel.is_set():raise Cancelled()
            export_figures(r,folder/'figures',language,separate,job.cancel)
            if r.metadata.get('diary'):pd.DataFrame(r.metadata['diary']).to_csv(folder/'diary.csv',index=False,encoding='utf-8-sig')
            job.progress.emit(100,r.label);job.item.emit(('exported',str(folder)))
        self.start_job(work)
    def apply_settings(self):
        if self.job and self.job.isRunning():return
        self.loaded_cfg=self.read_config();self.language=self.language_combo.currentData();self.theme=self.theme_combo.currentData();self.tutorials=self.tutorial_check.isChecked()
        self.settings.setValue('language',self.language);self.settings.setValue('theme',self.theme);self.settings.setValue('tutorials',self.tutorials);self.settings.setValue('separate',self.separate_check.isChecked());self.settings.sync()
        # Preserve the application data while rebuilding translated widgets.
        self.build();self.tabs.setCurrentIndex(5)
    def open_results(self):OUTPUT.mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT)))
    def open_manual(self,language):
        import shutil
        name='Manual_pt_BR' if language=='pt_BR' else 'Manual_en'
        for suffix in ['.pdf','.html']:
            path=BASE/'docs'/(name+suffix)
            embedded=RESOURCES/'docs'/(name+suffix)
            if embedded.exists() and embedded.resolve()!=path.resolve():
                path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(embedded,path)
            if path.exists():QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)));return
        self.tabs.setCurrentIndex(6)
    def open_report(self):
        import shutil
        for name in ['Relatorio_VoxDose_2.0.pdf','Relatorio_VoxDose_2.0.html','REPORT.md']:
            path=BASE/'docs'/name
            embedded=RESOURCES/'docs'/name
            if embedded.exists() and embedded.resolve()!=path.resolve():
                path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(embedded,path)
            if path.exists():QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)));return
    def closeEvent(self,event):
        if self.job and self.job.isRunning():
            self.cancel_job();self.statusBar().showMessage(self.T('Aguarde o cancelamento e feche novamente.','Wait for cancellation, then close again.'));event.ignore();return
        for dialog in list(self.plot_dialogs):dialog.close()
        event.accept()

def main():
    self_test='--self-test' in sys.argv
    smoke='--smoke-test' in sys.argv
    if smoke:os.environ['QT_QPA_PLATFORM']='offscreen'
    (BASE/'logs').mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=BASE/'logs'/'voxdose.log',level=logging.INFO,encoding='utf-8',format='%(asctime)s %(levelname)s %(message)s')
    app=QApplication.instance() or QApplication(sys.argv);app.setApplicationName('VoxDose 2.0');app.setOrganizationName(AUTHOR)
    app.setStyle('Fusion');app.setFont(QFont('Helvetica Neue' if sys.platform=='darwin' else 'Segoe UI',10));app.setWindowIcon(QIcon(str(ASSETS/'icon.svg')))
    if (smoke or self_test) and sys.platform=='win32':
        from PySide6.QtGui import QFontDatabase
        for font in ['segoeui.ttf','segoeuib.ttf','seguisb.ttf','seguisym.ttf']:
            QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    w=MainWindow();w.show()
    if self_test:
        from .verification import run_self_test
        QTimer.singleShot(200,lambda:run_self_test(app,w))
    if smoke:
        def verify():
            out=BASE/'validation';out.mkdir(parents=True,exist_ok=True)
            try:
                example=BASE/'examples'/'Synthetic_A.voxdose'
                if example.exists():
                    r=load_session(example);w.results.append(r);w.selector.addItem(r.label,0);w.selector.setCurrentIndex(1);w.tabs.setCurrentIndex(1)
                    cfg=Config(**r.metadata['config'])
                    cfg.calibration=[{'path':str(BASE/'examples'/'synthetic_calibration.wav'),'level':75.}]
                    actual=analyze(BASE/'examples'/'Synthetic_A.flac',cfg)
                    if not actual.summary['dt_s']>0 or actual.summary['cpps_db'] is None:
                        raise ValueError('Packaged audio analysis did not return voicing/CPPS.')
                app.processEvents();w.grab().save(str(out/'executable_smoke.png'))
                (out/'executable_smoke.json').write_text(json_text({'ok':True,'tabs':w.tabs.count(),'version':__version__,
                    'sample_loaded':w.current_result() is not None,'sample_audio_analyzed':example.exists(),
                    'analysis_frames':len(actual.frames) if example.exists() else 0,
                    'frozen':bool(getattr(sys,'frozen',False)),
                    'executable':sys.executable,'base':str(BASE)}),encoding='utf-8')
                app.quit()
            except Exception as e:
                logging.exception('Smoke test failed');(out/'executable_smoke.json').write_text(json_text({'ok':False,'error':str(e)}),encoding='utf-8');app.exit(1)
        QTimer.singleShot(100,verify)
    sys.exit(app.exec())

if __name__=='__main__':main()
