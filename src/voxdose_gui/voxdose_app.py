# voxdose_gui/voxdose_app.py
import sys
import os
import shutil
import subprocess
import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QVBoxLayout, QHBoxLayout, QDialog, QFileDialog, QLabel,
    QMessageBox, QComboBox, QDoubleSpinBox, QSpinBox, QInputDialog, QFrame, QSizePolicy
)
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtCore import Qt, QLocale

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np

# Your helper (kept; we’ll use it as a fallback)
from .paths import asset_path

# Splash and core
from voxdose_gui.splash import show_splash_screen
from voxdose_core.analyze_wav_spl_f0 import analyze_wav_spl_f0

# Optional summary-figure renderer (don’t break if not present)
try:
    from voxdose_reports import render_summary_figure
except Exception:
    render_summary_figure = None

PKG_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PKG_ROOT / "assets"
LOGO_PNG = ASSETS_DIR / "logo.png"
LOGO_ICO = ASSETS_DIR / "logo.ico"

# Force en_US locale (decimal dot)
QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))

def excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

BG_COLOR = "#CDCDC1"


def _resolve_asset(name: str) -> str:
    """
    Robust asset resolver:
    1) src/assets/name
    2) packaged asset via asset_path(name)
    3) current working dir (last resort)
    Returns a string path; may point to a non-existing file if nothing is found.
    """
    # 1) src/assets
    p1 = ASSETS_DIR / name
    if p1.exists():
        return str(p1)

    # 2) packaged resource (your helper)
    try:
        p2 = Path(asset_path(name))
        if p2.exists():
            return str(p2)
    except Exception:
        pass

    # 3) CWD (for manual runs)
    p3 = Path(name)
    return str(p3)


def _safe_logo_pixmap(height_px: int) -> QPixmap:
    """
    Load the PNG logo safely and scale to requested height.
    Avoids “null pixmap” warnings when path is wrong.
    """
    logo_path = _resolve_asset("logo.png")
    pm = QPixmap(logo_path)
    if pm.isNull():
        # As a last resort, return an empty pixmap of the correct size
        # (prevents warnings and preserves layout)
        fallback = QPixmap(height_px, int(height_px * 1.2))
        fallback.fill(Qt.transparent)
        return fallback
    return pm.scaledToHeight(height_px, Qt.SmoothTransformation)


class VoxDoseApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoxDose Analyzer v1.0.0")
        self.setGeometry(100, 100, 1000, 720)

        # Set the window icon here as well (in addition to __main__)
        icon_path = _resolve_asset("logo.ico")
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))

        # File paths and data
        self.wav_file = None                # Monitoring audio file (.wav/.mp3)
        self.cal_file = None                # Calibration audio (.wav/.mp3)
        self.save_folder = None             # Destination folder for results
        self.last_excel_file = None

        # Sex (now string): 'male' | 'female' | 'other'
        self.gender_mode = 'male'
        self.gender_other_notes = ""        # Free text when user selects Other…

        # Data for plotting
        self.time = None
        self.dB = None
        self.F0 = None

        # Defaults
        self.freq_low = 50
        self.freq_high = 300
        self.distance_cal = 0.30  # meters

        self.setup_ui()

    def setup_ui(self):
        font = QFont("Segoe UI", 11)
        main_layout = QVBoxLayout()

        # -- Top layout: left logo (fixed width), centered controls in a card, right pad --
        top_row = QHBoxLayout()
        top_row.setSpacing(24)

        # Left column with a bigger logo (fixed width stabilizes centering)
        left_col = QWidget()
        left_col.setFixedWidth(260)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        logo_label = QLabel()
        logo_pixmap = _safe_logo_pixmap(220)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        left_layout.addWidget(logo_label, alignment=Qt.AlignLeft | Qt.AlignTop)
        left_layout.addStretch(1)

        # Center controls in a "card"
        controls_widget = QFrame()
        controls_widget.setObjectName("card")
        controls_widget.setMaximumWidth(980)  # keeps it tidy and centered
        controls_layout = QVBoxLayout()
        controls_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        controls_layout.setContentsMargins(20, 16, 20, 16)
        controls_layout.setSpacing(12)

        # --- Monitoring file (WAV/MP3) ---
        btn_select = QPushButton("Select Monitoring Audio (WAV/MP3)")
        btn_select.setFont(font)
        btn_select.setMinimumWidth(320)
        btn_select.clicked.connect(self.select_file)
        btn_select.setStyleSheet("""
            QPushButton {
                background-color: #388e3c; color: white; border-radius: 8px; padding: 8px 22px;
            }
            QPushButton:hover, QPushButton:focus { background-color: #66bb6a; color: #f8f8f8; }
        """)
        controls_layout.addWidget(btn_select, alignment=Qt.AlignHCenter)

        self.label_file = QLabel("No monitoring file selected.")
        self.label_file.setFont(font)
        self.label_file.setStyleSheet("color: #555;")
        controls_layout.addWidget(self.label_file, alignment=Qt.AlignHCenter)

        # --- Calibration (file + level) ---
        cal_title = QLabel("Calibration (upload one file + enter meter SPL):")
        cal_title.setFont(font)
        controls_layout.addWidget(cal_title, alignment=Qt.AlignLeft)

        cal_row1 = QHBoxLayout()
        btn_cal = QPushButton("Select Calibration File (.wav/.mp3)")
        btn_cal.setFont(font)
        btn_cal.clicked.connect(self.select_calibration_file)
        cal_row1.addWidget(btn_cal)

        self.label_cal = QLabel("No calibration file selected.")
        self.label_cal.setFont(font)
        self.label_cal.setStyleSheet("color: #555;")
        cal_row1.addWidget(self.label_cal)
        controls_layout.addLayout(cal_row1)

        cal_row2 = QHBoxLayout()
        cal_row2.addWidget(QLabel("Calibration level (dBA):"))
        self.spin_cal_level = QDoubleSpinBox()
        self.spin_cal_level.setRange(40.0, 120.0)
        self.spin_cal_level.setDecimals(1)
        self.spin_cal_level.setSingleStep(0.1)
        self.spin_cal_level.setValue(82.9)
        self.spin_cal_level.setSuffix(" dBA")
        self.spin_cal_level.setFixedWidth(120)
        cal_row2.addWidget(self.spin_cal_level)
        controls_layout.addLayout(cal_row2)

        # --- Mic distance ---
        dist_layout = QHBoxLayout()
        dist_layout.addWidget(QLabel("Mic Distance (m):"))
        self.spin_dist = QDoubleSpinBox()
        self.spin_dist.setRange(0.05, 1.00)
        self.spin_dist.setDecimals(2)
        self.spin_dist.setSingleStep(0.01)
        self.spin_dist.setValue(self.distance_cal)
        self.spin_dist.setSuffix(" m")
        self.spin_dist.setFixedWidth(120)
        dist_layout.addWidget(self.spin_dist)
        controls_layout.addLayout(dist_layout)

        # --- Frequency settings ---
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("F0 range (Hz):"))
        self.spin_f_low = QSpinBox()
        self.spin_f_low.setRange(20, 2000)
        self.spin_f_low.setFixedWidth(100)
        self.spin_f_high = QSpinBox()
        self.spin_f_high.setRange(20, 2000)
        self.spin_f_high.setFixedWidth(100)
        self.spin_f_low.setValue(self.freq_low)
        self.spin_f_high.setValue(self.freq_high)
        freq_layout.addWidget(QLabel("Low:"))
        freq_layout.addWidget(self.spin_f_low)
        freq_layout.addSpacing(8)
        freq_layout.addWidget(QLabel("High:"))
        freq_layout.addWidget(self.spin_f_high)
        controls_layout.addLayout(freq_layout)

        # --- Sex ---
        gender_row = QHBoxLayout()
        gender_row.addWidget(QLabel("Sex:"))
        self.gender_box = QComboBox()
        self.gender_box.addItems(["Male", "Female", "Other…"])
        self.gender_box.currentIndexChanged.connect(self.set_gender_mode)
        self.gender_box.setFixedWidth(140)
        gender_row.addWidget(self.gender_box)
        controls_layout.addLayout(gender_row)

        # --- Save folder ---
        save_row = QHBoxLayout()
        btn_save_folder = QPushButton("Select Save Folder")
        btn_save_folder.setFont(font)
        btn_save_folder.clicked.connect(self.select_save_folder)
        save_row.addWidget(btn_save_folder)

        self.label_save = QLabel("No save folder selected (defaults to input file folder).")
        self.label_save.setFont(font)
        self.label_save.setStyleSheet("color: #555;")
        save_row.addWidget(self.label_save)
        controls_layout.addLayout(save_row)
        # Keep long paths on a single line and allow selection
        for lab in (self.label_file, self.label_cal, self.label_save):
            lab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lab.setWordWrap(False)
            lab.setMinimumWidth(700)
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)

        controls_widget.setLayout(controls_layout)

        # Right pad (same width as left) to keep the center perfectly centered
        right_pad = QWidget()
        right_pad.setFixedWidth(260)

        # Assemble row
        top_row.addWidget(left_col)
        top_row.addStretch(1)
        top_row.addWidget(controls_widget, alignment=Qt.AlignTop)
        top_row.addStretch(1)
        top_row.addWidget(right_pad)

        main_layout.addLayout(top_row)

        # --- Status label ---
        self.label_status = QLabel("\n")
        self.label_status.setFont(font)
        self.label_status.setStyleSheet("color: #333;")
        main_layout.addWidget(self.label_status)

        # --- Results plot area ---
        self.canvas = FigureCanvas(plt.figure(figsize=(10, 6)))
        main_layout.addWidget(self.canvas, stretch=1)

        # --- Bottom action buttons ---
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        btn_run = QPushButton("Run Analysis")
        btn_run.setFont(font)
        btn_run.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_run.clicked.connect(self.run_analysis)
        action_layout.addWidget(btn_run)

        btn_open_excel = QPushButton("Open Excel Results")
        btn_open_excel.setFont(font)
        btn_open_excel.setStyleSheet("background-color: #2196F3; color: white;")
        btn_open_excel.clicked.connect(self.open_excel_file)
        action_layout.addWidget(btn_open_excel)

        btn_about = QPushButton("About")
        btn_about.setFont(font)
        btn_about.setStyleSheet("background-color: #9E9E9E; color: white;")
        btn_about.clicked.connect(self.show_about)
        action_layout.addWidget(btn_about)

        btn_exit = QPushButton("Exit")
        btn_exit.setFont(font)
        btn_exit.setStyleSheet("background-color: #f44336; color: white;")
        btn_exit.clicked.connect(QApplication.instance().quit)
        action_layout.addWidget(btn_exit)

        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        container = QWidget()
        container.setLayout(main_layout)
        container.setStyleSheet(f"background-color: {BG_COLOR};")
        self.setCentralWidget(container)
        self.setStyleSheet(f"background-color: {BG_COLOR};")

        # keep your BG color
        self.setStyleSheet(f"background-color: {BG_COLOR};")

        # append the card style (for QFrame with objectName 'card')
        self.setStyleSheet(self.styleSheet() + """
        QFrame#card {
            background: #F7F7F7;
            border: 1px solid rgba(0,0,0,0.12);
            border-radius: 12px;
        }
        """)

    # ---------- gender handling ----------
    def set_gender_mode(self, index: int):
        if index == 0:
            self.gender_mode = 'male'
            self.spin_f_low.setValue(50)
            self.spin_f_high.setValue(300)
        elif index == 1:
            self.gender_mode = 'female'
            self.spin_f_low.setValue(100)
            self.spin_f_high.setValue(500)
        else:
            self.gender_mode = 'other'
            self.spin_f_low.setValue(50)
            self.spin_f_high.setValue(400)
            text, ok = QInputDialog.getMultiLineText(
                self, "Other – details",
                "Describe the voice characteristics or reason for 'Other' (optional):",
                self.gender_other_notes or ""
            )
            if ok:
                self.gender_other_notes = text or ""

    # ---------- allow WAV or MP3 ----------
    def select_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Audio files (*.wav *.WAV *.mp3 *.MP3)")
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                # Set new monitoring file
                self.wav_file = files[0]
                self.label_file.setText(f"Monitoring: {self.wav_file}")

                # Clear any previous calibration selection
                self.cal_file = None
                self.label_cal.setText("No calibration file selected.")

    def select_calibration_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Audio files (*.wav *.WAV *.mp3 *.MP3)")
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                self.cal_file = files[0]
                self.label_cal.setText(f"Calibration: {self.cal_file}")

    def select_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder", os.getcwd())
        if folder:
            self.save_folder = folder
            self.label_save.setText(f"Save folder: {self.save_folder}")

    def run_analysis(self):
        if not self.wav_file:
            QMessageBox.warning(self, "No File", "Please select a monitoring audio file (WAV/MP3) first.")
            return

        # Allow running UNCALIBRATED (no calibration file)
        uncalibrated = not bool(self.cal_file)

        if uncalibrated:
            resp = QMessageBox.question(
                self,
                "Confirm uncalibrated run",
                "No calibration file provided.\nRun analysis UNCALIBRATED?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                self.label_status.setText("Analysis canceled.")
                return

        # If UNCALIBRATED: skip both prompts (50 cm and “Did you…”) entirely
        if uncalibrated:
            use_50cm = False
            cal_level = None
            cal_file_arg = None
        else:
            # Prompt 1: 50 cm reference?
            ans = QMessageBox.question(
                self,
                "Reference distance",
                "Report SPL referenced to 50 cm?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            use_50cm = (ans == QMessageBox.Yes)

            # Prompt 2: confirm calibration level entry
            ans_cal = QMessageBox.question(
                self,
                "Calibration level check",
                "Did you enter the Calibration Level (dBA) for the calibration file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if ans_cal == QMessageBox.No:
                QMessageBox.information(
                    self,
                    "Action needed",
                    "Please enter the Calibration Level (dBA) and run again."
                )
                return

            cal_level = float(self.spin_cal_level.value())
            cal_file_arg = self.cal_file

        try:
            self.label_status.setText("Running analysis... please wait.")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # Inputs
            freq_low = self.spin_f_low.value()
            freq_high = self.spin_f_high.value()
            distance_cal = float(self.spin_dist.value())

            # If UNCALIBRATED, keep current mic distance; do NOT force 50 cm
            target_distance_m = 0.50 if (not uncalibrated and use_50cm) else distance_cal
            target_cm = int(round(target_distance_m * 100))

            # Run analysis (passes None when uncalibrated)
            orig_cwd = os.getcwd()
            work_dir = os.path.dirname(os.path.abspath(self.wav_file))
            os.chdir(work_dir)
            try:
                results, _ = analyze_wav_spl_f0(
                    fname=self.wav_file,
                    gender_mode=self.gender_mode,
                    calibration_file=cal_file_arg,
                    calibration_level_dBA=cal_level,
                    freq_low=freq_low,
                    freq_high=freq_high,
                    distance_cal=distance_cal,
                    target_distance_m=target_distance_m
                )
            finally:
                os.chdir(orig_cwd)

            results = np.array(results)
            # Default output path next to the monitoring file
            self.last_excel_file = self.wav_file
            for ext in (".wav", ".WAV", ".mp3", ".MP3"):
                if self.last_excel_file.endswith(ext):
                    self.last_excel_file = self.last_excel_file[:-len(ext)] + ".xlsx"
                    break

            # Extract arrays for plotting
            if results.ndim == 2 and results.shape[1] >= 3:
                self.time = results[:, 0]
                self.dB = results[:, 1]
                self.F0 = results[:, 2]
            elif results.ndim == 1 and len(results) == 3:
                self.time = np.array([results[0]])
                self.dB = np.array([results[1]])
                self.F0 = np.array([results[2]])
            else:
                raise ValueError("Unexpected result shape from analysis.")

            # Move outputs to save folder (if selected)
            input_dir = os.path.dirname(self.wav_file)
            base = os.path.splitext(self.wav_file)[0]
            target_png = f"{base}_Summary_{target_cm}cm.png"

            produced = [
                f"{base}.xlsx",
                f"{base}_VocalDoses.xlsx",
                target_png,
                os.path.join(input_dir, "SPL_plot.png"),
                os.path.join(input_dir, "SPL_dBA_plot.png"),
            ]

            if self.save_folder:
                for p in produced:
                    if os.path.exists(p):
                        dest = os.path.join(self.save_folder, os.path.basename(p))
                        try:
                            if os.path.abspath(p) != os.path.abspath(dest):
                                shutil.move(p, dest)
                            if p.lower().endswith(".xlsx") and os.path.basename(p) == os.path.basename(f"{base}.xlsx"):
                                self.last_excel_file = dest
                        except Exception as move_err:
                            print(f"[move] Could not move {p} -> {dest}: {move_err}")
                self.label_status.setText(f"Analysis complete. Results saved to: {self.save_folder}")
            else:
                self.label_status.setText("Analysis complete. Results saved next to the input file.")

            # ---------- PNG export fallback (if core didn’t write them) ----------
            try:
                out_dir = self.save_folder if self.save_folder else input_dir
                os.makedirs(out_dir, exist_ok=True)

                base_no_ext = os.path.splitext(os.path.basename(self.wav_file))[0]
                summary_png = os.path.join(out_dir, f"{base_no_ext}_Summary_{target_cm}cm.png")
                spl_png = os.path.join(out_dir, "SPL_plot.png")
                spl_dba_png = os.path.join(out_dir, "SPL_dBA_plot.png")

                # SPL simple plot
                if self.time is not None and self.dB is not None and not os.path.exists(spl_png):
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as _plt
                    fig = _plt.figure(figsize=(10, 3.2))
                    ax = fig.add_subplot(1, 1, 1)
                    dB_mask = self.dB > 0
                    ax.plot(self.time[dB_mask], self.dB[dB_mask], linewidth=1.2)
                    ax.set_title(f"SPL (dBA) @ {target_cm} cm")
                    ax.set_xlabel("Time (s)")
                    ax.set_ylabel("Level (dBA)")
                    fig.tight_layout()
                    fig.savefig(spl_png, dpi=200, bbox_inches="tight")
                    _plt.close(fig)

                # SPL dBA plot (alternate title)
                if self.time is not None and self.dB is not None and not os.path.exists(spl_dba_png):
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as _plt
                    fig = _plt.figure(figsize=(10, 3.2))
                    ax = fig.add_subplot(1, 1, 1)
                    dB_mask = self.dB > 0
                    ax.plot(self.time[dB_mask], self.dB[dB_mask], linewidth=1.2)
                    ax.set_title(f"SPL (dBA) timeline @ {target_cm} cm")
                    ax.set_xlabel("Time (s)")
                    ax.set_ylabel("Level (dBA)")
                    fig.tight_layout()
                    fig.savefig(spl_dba_png, dpi=200, bbox_inches="tight")
                    _plt.close(fig)

                # Summary figure via voxdose_reports if available
                if render_summary_figure and not os.path.exists(summary_png):
                    # 0.05 s analysis grid
                    if self.time is not None and self.time.size > 1:
                        t0, t1 = float(self.time[0]), float(self.time[-1])
                        step = 0.05
                        import numpy as _np
                        T = _np.arange(t0, t1 + step / 2, step)

                        # nearest-neighbor sampling
                        def _nn(sample_t, sample_y, new_t):
                            idx = _np.clip(_np.searchsorted(sample_t, new_t), 0, sample_t.size - 1)
                            return sample_y[idx]

                        dB_resampled = _nn(self.time, self.dB, T) if self.dB is not None else _np.zeros_like(T)
                        F0_resampled = _nn(self.time, self.F0, T) if self.F0 is not None else _np.zeros_like(T)

                        F0_mean = F0_resampled.copy()
                        CPPS = _np.zeros_like(T)
                        CPPS_mean = CPPS.copy()

                        SPL_valid = dB_resampled[dB_resampled > 0]
                        F0_valid = F0_resampled[F0_resampled > 0]
                        SPL_mean = float(_np.mean(SPL_valid)) if SPL_valid.size else 0.0
                        F0_mean_scalar = float(_np.mean(F0_valid)) if F0_valid.size else 0.0

                        dose_tuple = (
                            0.0, 0.0, 0.0, 0.0, 0.0,
                            0.0, 0.0, 0.0, 0.0,
                            SPL_mean, F0_mean_scalar,
                            float(_np.std(SPL_valid)) if SPL_valid.size else 0.0,
                            float(_np.std(F0_valid)) if F0_valid.size else 0.0
                        )

                        render_summary_figure(
                            time_vector=self.time, x=_np.zeros_like(self.time),
                            windowTime=T, dB=dB_resampled,
                            F0=F0_resampled, F0_mean_t=F0_mean,
                            CPPS=CPPS, CPPS_mean_t=CPPS_mean,
                            dist_cm=target_cm,
                            distance_cal=distance_cal,
                            is_calibrated=(self.cal_file is not None),
                            dose=dose_tuple,
                            base=os.path.join(out_dir, base_no_ext)
                        )
            except Exception as e_png:
                print(f"[PNG fallback] Skipped due to: {e_png}")
            # -------------------------------------------------------

            self.plot_results()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")
            self.label_status.setText("Analysis failed.")
        finally:
            QApplication.restoreOverrideCursor()

    def plot_results(self):
        self.canvas.figure.clear()

        dB_valid = self.dB[self.dB > 0] if self.dB is not None else np.array([])
        F0_valid = self.F0[self.F0 > 0] if self.F0 is not None else np.array([])
        dB_mean = float(np.mean(dB_valid)) if dB_valid.size else 0.0
        F0_mean = float(np.mean(F0_valid)) if F0_valid.size else 0.0

        ax1 = self.canvas.figure.add_subplot(2, 1, 1)
        if self.time is not None and self.dB is not None:
            ax1.plot(self.time, self.dB, color="#4CAF50")
        ax1.set_title("Sound Pressure Level (SPL)")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Level (dBA)")
        ax1.annotate(
            f"Mean SPL: {dB_mean:.1f} dBA",
            xy=(0.5, 1.16), xycoords="axes fraction",
            ha="center", va="center", fontsize=11, fontweight='bold', color="#4CAF50"
        )

        ax2 = self.canvas.figure.add_subplot(2, 1, 2)
        if self.time is not None and self.F0 is not None:
            ax2.plot(self.time, self.F0, color="#2196F3")
        ax2.set_title("Fundamental Frequency (F0)")
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Frequency (Hz)")
        ax2.annotate(
            f"Mean F0: {F0_mean:.1f} Hz",
            xy=(0.5, 1.16), xycoords="axes fraction",
            ha="center", va="center", fontsize=11, fontweight='bold', color="#2196F3"
        )

        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def open_excel_file(self):
        target = self.last_excel_file
        if not target or not os.path.exists(target):
            QMessageBox.warning(self, "No Excel File", "No result file found. Run an analysis first.")
            return

        try:
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.call(["open", target])
            else:
                subprocess.call(["xdg-open", target])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")

    def show_about(self):
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("About VoxDose")
        about_dialog.setFixedSize(800, 500)
        about_dialog.setStyleSheet("background-color: #CDCDC1;")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 30, 40, 20)
        main_layout.setSpacing(0)

        logo_and_text = QWidget()
        block_layout = QVBoxLayout()
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(2)

        logo = QLabel()
        logo_pixmap = _safe_logo_pixmap(150)
        logo.setPixmap(logo_pixmap)
        logo.setAlignment(Qt.AlignCenter)
        block_layout.addWidget(logo, alignment=Qt.AlignCenter)

        text = QLabel()
        text.setTextFormat(Qt.RichText)
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setFont(QFont("Segoe UI", 11))
        text.setText("""
            <h2>VoxDose</h2>
            <p><b>VoxDose</b> estimates vocal doses from audio recordings.</p>
            <p>It computes SPL (dBA) and fundamental frequency (F0), then derives:</p>
            <p>Phonation time, Vocal Loading Index (VLI), Energy and Radiation doses.</p>
            <p>Based on MATLAB code by Pasquale Bottalico.</p>
            <p style="margin-top:10px;">
                <i>Want to build your own voice dosimeter?</i><br/>
                See: Bottalico P, Nudelman CJ. <em>Do-It-Yourself Voice Dosimeter Device:
                A Tutorial and Performance Results.</em> J Speech Lang Hear Res. 2023;66(7):2149–2163.
                DOI: <a href="https://doi.org/10.1044/2023_JSLHR-23-00060">10.1044/2023_JSLHR-23-00060</a> |
                PubMed: <a href="https://pubmed.ncbi.nlm.nih.gov/37263017/">37263017</a>
            </p>
            <p>MIT Licensed – © 2025 FonoTech Academy</p>
        """)
        block_layout.addWidget(text, alignment=Qt.AlignCenter)

        logo_and_text.setLayout(block_layout)
        main_layout.addWidget(logo_and_text, alignment=Qt.AlignTop | Qt.AlignHCenter)

        about_dialog.setLayout(main_layout)
        about_dialog.exec()

    def close_application(self):
        QApplication.instance().quit()


def main():
    """Main entry point for the VoxDose application."""
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QApplication(sys.argv)
    app_icon = _resolve_asset("logo.ico")
    if Path(app_icon).exists():
        app.setWindowIcon(QIcon(app_icon))
    show_splash_screen(app)
    window = VoxDoseApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
