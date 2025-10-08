**Title: VoxDose: An Open-Source Software for Vocal Dose Analysis**

**Authors:** Tiago Lima Bicalho Cruz^a^ & Pasquale Bottalico^b^

^a^ Fonotech Academy, Belo Horizonte, Brazil

Correspondence: fonotechacademy@gmail.com

^b^ Department of Speech and Hearing Science, University of Illinois at
Urbana--Champaign

**Introduction**

The human voice is a complex biological and acoustic system that enables
speech, singing, and communication across professional and social
domains. For occupational voice users---including teachers, singers,
actors, broadcasters, and call-center operators---the voice is the
primary tool of the trade, and excessive vocal load can lead to fatigue,
dysphonia, and long-term injury \[@Titze1997; \@Hunter2016;
\@Vilkman2004\]. To address these risks, researchers have developed the
concept of vocal dose, which quantifies the cumulative vibration
exposure of the vocal folds in a manner analogous to radiation or
chemical exposure \[@Titze2003\].

Vocal dose measures include: time dose (Dt), or total phonation time;
cycle dose (Dc/VLI), the total number of oscillations; distance dose
(Dd), the cumulative distance traveled by the vocal folds; energy
dissipation dose (De), the mechanical energy absorbed by tissue; and
radiated energy dose (Dr), the acoustic energy radiated to the
environment \[@Titze2003; \@Švec2004\]. These parameters provide a
multidimensional perspective on vocal load, going beyond simple averages
of fundamental frequency (F0) and sound pressure level (SPL).

Since their formalization, vocal dose measures have been applied to a
wide range of populations and contexts. Teachers have been the most
frequently studied group, with evidence showing that classroom noise,
reverberation, and lack of amplification significantly increase vocal
doses and risk of dysphonia \[@Astolfi2012; \@Bottalico2012;
\@Assad2019; \@Rabelo2019\]. Studies confirm that teachers typically
spend around 25--27% of their working day phonating, corresponding to
hundreds of thousands of vocal fold oscillations and several kilometers
of cumulative tissue displacement \[@Astolfi2012; \@Bottalico2012\].
Amplification has been shown to significantly reduce cycle and distance
doses in dysphonic teachers \[@Assad2019\], while classroom noise
increases fundamental frequency, vocal intensity, percentage of
phonation (time dose), and cycle dose through the Lombard effect
\[@Rabelo2019\].

Vocal dose analysis has also expanded into singing and performance
\[@Carroll2006\]. Professional singers display higher doses than
untrained controls, but with more efficient respiratory--phonatory
coordination \[@Cunsolo2022\]. In contemporary musical theatre, singers
accumulate extremely high cycle and distance doses, particularly women,
due to stylistic demands of chest-dominant phonation. Self-perception,
as measured by the Evaluation of the Ability to Sing Easily (EASE)
questionnaire, showed poor correlation with objective exposure
\[@Zuim2024\].

Technological advances have shaped the field. The NCVS dosimeter (Titze
& Hunter, 2004) set the foundation for ambulatory monitoring using
neck-surface accelerometers. Commercial systems (APM, VoxLog, VocaLog,
Voice-Care) have since become available, though cost and limited
parameter extraction remain barriers \[@Hunter2016\]. Recent innovations
include smartphone-based systems \[@Castellana2018; \@Hunter2016;
\@Mehta2015\] and low-cost DIY solutions \[@Bottalico2023\], making
vocal dosimetry more accessible. Research has also integrated subglottal
impedance-based inverse filtering (IBIF) to estimate aerodynamic
parameters \[@Mehta2015\] and accelerometer-based prediction of
subglottal pressure \[@Fryd2016\], expanding the scope of ambulatory
monitoring.

Systematic reviews highlight consistent findings: high vocal doses are
linked to teaching, noisy environments, dysphonia, and vocal fatigue,
while amplification and vocal rest reduce exposure \[@Assad2017\].
Collectively, these studies demonstrate that vocal dose measures are
powerful tools for understanding occupational voice use, guiding
preventive strategies, and supporting clinical decision-making.

**Statement of Need**

Despite two decades of research into vocal dose, existing tools for
analysis remain either costly, closed-source, or inaccessible to
clinicians and researchers outside specialized laboratories. Teachers,
clinicians, and voice scientists often rely on proprietary dosimeters or
complex workflows requiring Praat scripting, MATLAB, or non-standardized
pipelines. There is a pressing need for an open-source, user-friendly,
and reproducible software that implements validated vocal dose metrics,
integrates SPL and F0 calibration, and exports standardized results for
research, pedagogy, and clinical practice.

VoxDose addresses this gap by providing a free, open-source application
that computes all major vocal dose measures (Dt, VLI, Dd, De, Dr) from
recorded audio, with calibration features, visualization, and batch
analysis. By bridging the gap between advanced voice science and
practical applications, VoxDose democratizes access to vocal dosimetry
for researchers, clinicians, and educators worldwide.

**Installation**

VoxDose is distributed as open-source Python code. The recommended
installation procedure is as follows:

**Prerequisites**

-   Python 3.9 or later (tested on Windows, macOS, Linux)

-   Required libraries: numpy, scipy, matplotlib, pandas, PySide6,
    > praat-parselmouth, openpyxl

**Step-by-step**

1.  Clone the repository:

2.  git clone https://github.com/tiagolbc/voxdose.git

3.  cd voxdose

4.  Install dependencies:

5.  pip install -r requirements.txt

6.  Run the application:

7.  python main_gui.py

**\
**

**Software Description**

**Purpose and Features**

-   Frame-by-frame analysis of Sound Pressure Level (SPL, dBA) and
    fundamental frequency (F0, Hz) from WAV or MP3 recordings.

-   Calculation of vocal dose metrics:

    -   Dt (phonation time),

    -   VLI (Vocal Loading Index, cycles × 1000),

    -   Dd (distance dose, meters),

    -   De (energy dissipation dose, joules),

    -   Dr (radiated energy dose, joules),

    -   plus normalized measures and SPL/F0 statistics.

-   Calibration (30 cm vowel + SLM): Users record a sustained vowel at
    30 cm while reading SPL on a calibrated sound level meter at the
    same position. VoxDose takes the calibration audio file and the
    measured SPL (dBA), computes a calibration constant, and applies it
    to the analysis. During processing, users can report SPL at 30 cm
    (default) or re-reference to 50 cm:

$$SPL_{target} = SPL_{measured} - 20\log_{\, 10}\left( \frac{d_{cal}}{d_{target}} \right)$$      


        
    - This correction ensures that all SPL values---and consequently all derived dose measures (Dt, VLI, Dd, De, Dr)---are expressed in absolute, physically valid units consistent with the selected reference distance.
    
-   Interactive Graphical User Interface (GUI) with:

    -   File selection (voice recordings and calibration recording for
        SPL).

    -   Input fields for SPL calibration, microphone distance, and F0
        search range.

    -   Sex-specific analysis paths (male, female, or "other") affecting
        biomechanical scaling.

    -   Export options for results in Excel (frame-by-frame and summary
        doses).

-   Visualization: SPL and F0 time series with automatic mean
    annotation; summary plots saved alongside results; spectrogram and
    pitch tracking available for advanced inspection.

**\
**

**Implementation and Architecture**

**Core modules**

-   **dosi.py** -- Implements all vocal dose equations (Dt, VLI, Dd, De,
    Dr), following Bottalico's MATLAB framework with sex-specific
    physiological scaling.

-   **spl_fast.py / spl_fast_c\_th.py** -- Frame-by-frame SPL
    computation kernels, with or without calibration constant.

-   **stima_livello.py** -- FFT-based SPL estimator used in calibration
    and validation.

-   **sp_pitch_praat.py and sp_pitch_track_praat.py** -- Parselmouth
    wrappers for Praat autocorrelation-based pitch extraction, used for
    both sustained vowels and connected speech.

-   **sp_cpps.py** -- CPPS estimation for connected speech, computed
    every 5 s on voiced segments after pause removal.

-   **analyze_wav_spl_f0.py** -- Central analysis routine: integrates
    SPL and F0 pipelines, runs calibration, synchronizes arrays, removes
    silences, and exports both frame-level data and summary dose
    results.

-   **main_gui.py** -- PySide6-based graphical interface providing file
    selection, calibration entry, analysis controls, plotting, and
    export.

-   **splash.py** -- Startup splash screen with license and credits.

**Analysis workflow**

1.  **Input**: user selects voice file(s), optional calibration file,
    enters measured SPL, and sets distance options.

2.  **Preprocessing**: SPL is computed with the calibration constant; F0
    is tracked with Praat autocorrelation; silences (\<50 dBA) are
    masked.

3.  **Synchronization**: SPL and F0 arrays are aligned at 50 ms frame
    resolution.

4.  **Dose computation**: dosi.py integrates the frame-based values into
    cumulative dose metrics.

5.  **Export**: results are written into two Excel files per recording:

    -   \[basename\].xlsx (time, SPL, F0 per frame).

    -   \[basename\]\_VocalDoses.xlsx (summary table with all dose
        metrics).

6.  **Visualization**: SPL and F0 plots with mean annotations, plus
    summary PNG plots of the dose metrics.

**Architecture**\
The modular structure separates signal processing (pitch, SPL,
cepstrum), mathematical modeling (dose equations), and user interface
(GUI, splash, exports). This design allows VoxDose to be easily extended
with new acoustic features (e.g., HNR, alpha ratio) or alternative
pitch/SPL methods, while maintaining a clean and reproducible analysis
pipeline.

**Illustrative Examples**

To illustrate the functionality of VoxDose, we present one analysis
example recorded by the first author. The test consisted of a sustained
vowel calibration followed by a short connected-speech passage.

The first step is shown in Figure 1, where the GUI allows the user to
select the voice recording, load the calibration file, enter the SPL
value measured with the sound level meter, and choose whether results
should be reported at 30 cm or re-referenced to 50 cm. The GUI provides
a simple and intuitive workflow, designed for researchers, clinicians,
and educators who may not have programming experience.

![](media/image1.PNG){width="6.17928915135608in"
height="4.495433070866142in"}

Figure 1. VoxDose graphical interface showing file selection,
calibration entry, distance options, and analysis controls.

Once the calibration and analysis are executed, VoxDose produces both
frame-level and summary outputs. Figure 2 illustrates the visualization
of SPL and F0 time series, with mean values automatically annotated, as
well as the export of cumulative vocal dose measures (Dt, VLI, Dd, De,
Dr) to an Excel file. This integration of graphical and tabular results
provides a comprehensive view of vocal load, making it possible to
interpret individual phonatory behavior in absolute units.

![](media/image2.png){width="5.905555555555556in" height="4.90625in"}

Figure 2. Example output generated by VoxDose: SPL and F0 curves over
time with mean annotations, alongside a summary table of vocal dose
metrics.

**Comparison with Existing Tools**

Vocal dosimetry research has historically relied on hardware-based
systems. Early solutions, such as speech timers and voice accumulators
\[@Ryu1983; \@Rantala1999\], initially focused on quantifying phonation
time, with later advancements incorporating measures like the total
number of vocal fold oscillations. More advanced devices, like the
KayPENTAX Ambulatory Phonation Monitor (APM 3200) and the NCVS dosimeter
\[@Švec2004\], introduced accelerometer-based monitoring of F0, SPL, and
phonation time, enabling the first large-scale studies of vocal load.
Commercial successors---including VocaLog2 (Griffin Labs), VoxLog
(Sonvox AB), and Voice-Care (PR.O.VOICE)---continue this tradition, but
remain hardware products with proprietary data formats, high costs, and
limited analytical flexibility \[@Hunter2016\].

Recent developments have explored DIY dosimeters \[@Bottalico2023\] and
smartphone-based solutions \[@Mehta2015\], expanding accessibility but
still tied to hardware for data collection. These devices generate raw
data streams (accelerometer, SPL, F0) that must then be processed into
meaningful measures of vocal dose.

VoxDose does not compete with these hardware systems, but instead
provides a software-only solution for analysis and visualization of
vocal dose metrics. It is designed to:

-   Process pre-recorded audio files (e.g., WAV) rather than raw accelerometer signals.

-   Implement validated mathematical models of vocal dose (Dt, VLI, Dd, De, Dr) \[@Titze2003; \@Bottalico2012\].

-   Integrate SPL calibration against sound level meter values, ensuring external consistency.

-   Offer open-source accessibility, in contrast to closed proprietary ecosystems.

-   Facilitate research and clinical practice where hardware dosimeters are not available, or where recordings need retrospective analysis.

In this sense, VoxDose is best understood as a complementary tool:
hardware dosimeters capture real-life ambulatory data, while VoxDose
provides a transparent, reproducible environment to analyze, visualize,
and export vocal dose measures from recorded speech or singing tasks.

**Acknowledgements**

The mathematical framework for vocal dose measures was originally
developed in MATLAB by Prof. Pasquale Bottalico (University of Illinois
at Urbana-Champaign). His algorithms served as the foundation for the
present Python reimplementation in VoxDose, ensuring continuity and
reproducibility.

VoxDose is part of the FonoTech Academy open-source ecosystem, dedicated
to making advanced voice science tools accessible, transparent, and
reproducible for researchers, clinicians, and educators worldwide.
