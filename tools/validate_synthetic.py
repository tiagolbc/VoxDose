"""End-to-end validation against independently specified synthetic ground truth.

The reference calculator uses scalar math and continuous segment durations,
not the production integrands or extracted audio features. Assigned SPL is
a numerical calibration contract, not a physical microphone measurement.
"""
from pathlib import Path
from dataclasses import asdict
import sys,math,json,time,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import soundfile as sf
from voxdose.core import Config,analyze
from voxdose.storage import json_text

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation'/'synthetic_ground_truth'
SIGNALS=OUT/'signals';SIGNALS.mkdir(parents=True,exist_ok=True)
SEED=20261115
SENSITIVITY=.05  # digital amplitude per assigned pascal
PREF=20e-6
ROWS=[];CASES=[];F0_ROWS=[]

def reference_doses(segments,model):
    """Independent continuous-time solutions to Titze equations 14-24."""
    totals={'dt_s':0.,'dc_cycles':0.,'dd_m':0.,'de_j_m3':0.,'dr_j':0.}
    for seconds,hz,spl in segments:
        if hz==0:continue
        totals['dt_s']+=seconds;totals['dc_cycles']+=seconds*hz
        branches=[]
        for sex in ['male','female']:
            nominal=120. if sex=='male' else 190.
            length=.016 if sex=='male' else .010
            thickness=(.0158 if sex=='male' else .01063)/(1+(2.15 if sex=='male' else 1.69)*math.sqrt(hz/nominal))
            threshold=.14+.06*(hz/nominal)**2
            pressure_excess=10**((spl-78.5)/27.3)
            amplitude=.05*length*math.sqrt(pressure_excess/threshold)
            viscosity=(5.4 if sex=='male' else 1.4)/hz
            distance=4*amplitude*hz*seconds
            energy=.5*viscosity*(amplitude/thickness)**2*(2*math.pi*hz)**2*seconds
            branches.append((distance,energy))
        selected=branches[0] if model=='male' else branches[1] if model=='female' else tuple((a+b)/2 for a,b in zip(*branches))
        totals['dd_m']+=selected[0];totals['de_j_m3']+=selected[1]
        totals['dr_j']+=4*math.pi*.5**2*10**((spl-120)/10)*seconds
    return totals

def synth_segment(fs,duration,hz,spl,harmonics=(1.,),snr=None,rng=None):
    n=round(duration*fs);t=np.arange(n)/fs
    if hz==0:return np.zeros(n)
    # Harmonic coefficients normalized analytically to the assigned RMS pressure.
    wave=sum(a*np.sin(2*math.pi*(k+1)*hz*t) for k,a in enumerate(harmonics))
    rms_pressure=PREF*10**(spl/20)
    wave*=math.sqrt(2)*rms_pressure*SENSITIVITY/math.sqrt(sum(a*a for a in harmonics))
    if snr is not None:
        sigma=rms_pressure*SENSITIVITY*10**(-snr/20)
        wave+=rng.normal(0,sigma,n)
    return wave

def record(case,measure,true,estimated,tolerance,unit,criterion='absolute',role='acceptance'):
    if estimated is None or not math.isfinite(float(estimated)):
        error=None;rel=None;passed=False
    else:
        error=abs(float(estimated)-true);rel=error/abs(true) if true else None
        passed=(error<=tolerance) if criterion=='absolute' else (rel is not None and rel<=tolerance)
    ROWS.append({'case':case,'measure':measure,'true':true,'estimated':estimated,'absolute_error':error,'relative_error':rel,
        'tolerance':tolerance,'criterion':criterion,'unit':unit,'role':role,'passed':bool(passed) if role=='acceptance' else None})

def calibration(fs):
    pts=[]
    for level in [60.,75.,90.]:
        path=SIGNALS/f'calibration_{fs}_{int(level)}dBZ.wav'
        sf.write(path,synth_segment(fs,3,1000,level),fs,subtype='FLOAT')
        pts.append({'path':str(path),'level':level})
    return pts

def evaluate_segments(name,segments,fs=16000,model='average',harmonics=(1.,),snr=None,check_doses=True):
    rng=np.random.default_rng(SEED)
    x=np.concatenate([synth_segment(fs,d,h,s,harmonics,snr,rng) for d,h,s in segments])
    path=SIGNALS/(name+'.wav');sf.write(path,x,fs,subtype='FLOAT')
    cfg=Config(f0_min=40,f0_max=1200,model=model,calibration=calibration(fs),calibration_weighting='Z',
        calibration_distance_m=.5,target_distance_m=.5,window_s=10,cpps=True,gate_spl=45,
        subject='SYNTHETIC_GROUND_TRUTH',task=name,device='known numerical pressure mapping')
    # A-weighted 50 Hz tones can be ~30 dB below their Z level. Use an explicit
    # low gate for this numerical detector test; do not mistake gate rejection
    # under a normal environmental threshold for a failure of the pitch tracker.
    cfg.gate_spl=20.
    start=time.perf_counter();r=analyze(path,cfg);elapsed=time.perf_counter()-start
    truth=reference_doses(segments,model);duration=sum(d for d,_,_ in segments)
    record(name,'duration_s',duration,r.summary['duration_s'],1/fs,'s')
    # At most one 50 ms frame per transition plus file-edge context tolerance.
    phon_tol=max(.1,.05*(len(segments)+1))
    record(name,'dt_s',truth['dt_s'],r.summary['dt_s'],phon_tol,'s')
    record(name,'dt_pct',truth['dt_s']/duration*100,r.summary['dt_pct'],phon_tol/duration*100,'%')
    tt=r.frames.center_s.to_numpy();gt_f=np.zeros(len(tt));gt_z=np.full(len(tt),np.nan);position=0.
    transition=np.zeros(len(tt),dtype=bool)
    for d,h,s in segments:
        mask=(tt>=position)&(tt<position+d);gt_f[mask]=h
        if h:gt_z[mask]=s
        transition|=(abs(tt-position)<.15)|(abs(tt-(position+d))<.15)
        position+=d
    valid=(gt_f>0)&~transition&r.frames.voiced.to_numpy()
    measured=r.frames.f0_hz.to_numpy()
    role='characterization' if snr is not None and snr<=0 else 'acceptance'
    err=np.abs(measured[valid]-gt_f[valid]);relative=err/gt_f[valid]
    record(name,'f0_median_absolute_error_hz',0.,float(np.median(err)) if len(err) else None,.5,'Hz',role=role)
    record(name,'f0_p95_relative_error',0.,float(np.quantile(relative,.95)) if len(err) else None,.01,'fraction',role=role)
    record(name,'f0_detection_recall',1.,float(np.mean(r.frames.voiced.to_numpy()[(gt_f>0)&~transition])),.02,'fraction',role=role)
    if valid.any():
        F0_ROWS.extend({'case':name,'true_hz':float(g),'estimated_hz':float(e)} for g,e in zip(gt_f[valid][::10],measured[valid][::10]))
    if check_doses:
        record(name,'dc_cycles',truth['dc_cycles'],r.summary['dc_cycles'],.015,'cycles',criterion='relative')
        for key,unit in [('dd_m','m'),('de_j_m3','J/m3'),('dr_j','J')]:
            record(name,key,truth[key],r.summary[key],.02,unit,criterion='relative')
        record(name,'spl_z_median_error_db',0.,float(np.median(abs(r.frames.spl_z_db.to_numpy()[valid]-gt_z[valid]))) if valid.any() else None,.05,'dB')
    CASES.append({'name':name,'sample_rate':fs,'segments':segments,'harmonics':harmonics,'snr_db':snr,
        'model':model,'truth':truth,'measured_summary':r.summary,'seconds_to_analyze':elapsed,
        'config':asdict(cfg),'signal_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'cpps_note':'No analytical CPPS/HNR ground truth is assigned. Values are characterized, not claimed validated.'})
    print(name, 'done',flush=True)
    return r

def main():
    if (OUT/'summary.json').exists():
        import shutil
        from datetime import datetime
        history=OUT/'history'/datetime.now().strftime('%Y%m%d_%H%M%S');history.mkdir(parents=True)
        for name in ['summary.json','measurements.csv','ground_truth.json','VALIDATION.md']:
            if (OUT/name).exists():shutil.copy2(OUT/name,history/name)
    for name,freq,level,model,fs,harm in [
        ('steady_120Hz_70dBZ',120,70,'male',16000,(1.,)),
        ('steady_240Hz_80dBZ',240,80,'female',44100,(1.,)),
        ('harmonic_200Hz_75dBZ',200,75,'average',48000,(1.,.4,.2)),
        ('low_50Hz_65dBZ',50,65,'average',16000,(1.,.35)),
        ('high_800Hz_75dBZ',800,75,'average',48000,(1.,.2)),
        ('noninteger_sample_grid_190Hz',190,72,'average',11025,(1.,.3))]:
        evaluate_segments(name,[(20.,freq,level)],fs,model,harm)
    evaluate_segments('level_steps_200Hz',[(10,200,60),(10,200,70),(10,200,80)])
    evaluate_segments('pitch_steps',[(10,120,75),(10,200,75),(10,300,75)])
    evaluate_segments('voicing_and_pauses',[(5,0,0),(10,200,75),(2,0,0),(10,200,75),(5,0,0)])
    evaluate_segments('partial_final_frame',[(12.123,200,75)],check_doses=True)
    for snr in [30,10,0]:evaluate_segments(f'harmonic_noise_snr_{snr}dB',[(20,200,75)],harmonics=(1.,.35,.15),snr=snr,check_doses=False)
    # Pure noise has known zero periodic source; detection false positives are measurable.
    rng=np.random.default_rng(SEED);fs=16000;x=rng.normal(0,.01,fs*20)
    p=SIGNALS/'aperiodic_white_noise.wav';sf.write(p,x,fs,subtype='FLOAT')
    r=analyze(p,Config(f0_min=40,f0_max=1200,cpps=False))
    record('aperiodic_white_noise','voicing_false_positive_fraction',0.,r.summary['dt_pct']/100,.02,'fraction')
    # Linear chirp: analytical instantaneous f(t), independent of the pitch extractor.
    fs=16000;duration=30.;t=np.arange(fs*30)/fs;f_start=100.;slope=10.
    phase=2*np.pi*(f_start*t+.5*slope*t*t);x=.05*np.sin(phase)
    p=SIGNALS/'linear_chirp_100_400Hz.wav';sf.write(p,x,fs,subtype='FLOAT')
    r=analyze(p,Config(f0_min=40,f0_max=600,cpps=False));g=f_start+slope*r.frames.center_s.to_numpy()
    keep=r.frames.voiced.to_numpy()&(r.frames.center_s>.2)&(r.frames.center_s<29.8)
    record('linear_chirp_100_400Hz','f0_median_absolute_error_hz',0.,float(np.median(abs(r.frames.f0_hz.to_numpy()[keep]-g[keep]))),.5,'Hz')
    record('linear_chirp_100_400Hz','dc_cycles',f_start*duration+.5*slope*duration**2,r.summary['dc_cycles'],.01,'cycles',criterion='relative')
    # A weighting: harmonic-energy reference uses nominal analog response, not the digital filter.
    fs=48000;harm=(1.,.5,.25);f0=200;level=75
    r=evaluate_segments('A_weighted_harmonic_check',[(20,f0,level)],fs=fs,harmonics=harm)
    def nominal_a(f):
        q=f*f
        response=12194**2*q*q/((q+20.6**2)*math.sqrt((q+107.7**2)*(q+737.9**2))*(q+12194**2))
        return 20*math.log10(response)+2
    expected=level+10*math.log10(sum(a*a*10**(nominal_a((i+1)*f0)/10) for i,a in enumerate(harm))/sum(a*a for a in harm))
    record('A_weighted_harmonic_check','spl_a_mean',expected,r.summary['spl_a_mean'],.15,'dBA')
    # Explicit analytical ground truth for the previously run two-hour stream.
    long_path=ROOT/'validation'/'long_audio'/'benchmark.json'
    if long_path.exists():
        b=json.loads(long_path.read_text());s=b['summary']
        record('two_hour_stream','duration_s',7200,s['duration_s'],1e-6,'s')
        record('two_hour_stream','dt_s',720*4,s['dt_s'],.1,'s')
        record('two_hour_stream','dc_cycles',720*4*180,s['dc_cycles'],.001,'cycles',criterion='relative')
        record('two_hour_stream','dt_pct',40.,s['dt_pct'],.002,'%')
    frame=pd.DataFrame(ROWS);frame.to_csv(OUT/'measurements.csv',index=False,encoding='utf-8-sig')
    accept=frame[frame.role=='acceptance'];fail=accept[~accept.passed.astype(bool)]
    summary={'seed':SEED,'acceptance_checks':len(accept),'passed':len(accept)-len(fail),'failed':len(fail),
        'characterization_checks':int((frame.role=='characterization').sum()),'cases':len(set(frame.case)),
        'numerical_sensitivity_digital_per_pa':SENSITIVITY,'pressure_reference_pa':PREF,
        'cpps_hnr_ground_truth':False,
        'limitations':['Assigned SPL is a numerical calibration contract, not a physical microphone validation.',
            'The independent scalar reference verifies code against model equations, not the biological accuracy of the model.',
            'CPPS/HNR have no assigned analytical ground truth here; no accuracy claim is made for them.',
            'Results from clean periodic signals do not establish validity in dysphonic voices, real environments or contact sensors.'],
        'failed_checks':fail.to_dict(orient='records')}
    (OUT/'summary.json').write_text(json_text(summary),encoding='utf-8')
    (OUT/'ground_truth.json').write_text(json_text({'seed':SEED,'cases':CASES}),encoding='utf-8')
    import runpy
    runpy.run_path(str(ROOT/'tools'/'complete_ground_truth_metadata.py'))
    make_figure(frame,pd.DataFrame(F0_ROWS))
    lines=['# Validação sintética com ground truth conhecido','',
        f"{summary['passed']}/{summary['acceptance_checks']} critérios de aceitação aprovados; {summary['failed']} falhas. {summary['characterization_checks']} verificações descritivas sem critério de aprovação.",'',
        'Os valores de referência são definidos na síntese e em um cálculo escalar independente das funções de produção. O SPL é uma atribuição numérica conhecida, sem validação de microfone físico. CPPS/HNR não possuem ground truth analítico nesta bateria.','',
        '| Caso | Medida | Esperado | Obtido | Erro absoluto | Critério | Aprovado |','|---|---|---:|---:|---:|---|---|']
    for row in ROWS:
        true=f"{row['true']:.8g}";est=f"{row['estimated']:.8g}" if row['estimated'] is not None else 'NA';err=f"{row['absolute_error']:.5g}" if row['absolute_error'] is not None else 'NA'
        lines.append(f"| {row['case']} | {row['measure']} | {true} | {est} | {err} | {row['criterion']} <= {row['tolerance']:g} | {row['passed']} |")
    (OUT/'VALIDATION.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json_text(summary))
    if len(fail):raise SystemExit(1)

def make_figure(data,f0):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig=Figure(figsize=(12,5.2),dpi=160,layout='constrained');FigureCanvasAgg(fig);axs=fig.subplots(1,2)
    ax=axs[0]
    if len(f0):
        ax.scatter(f0.true_hz,f0.estimated_hz,s=6,alpha=.22,color='#087F8C');ax.plot([30,850],[30,850],color='#243C52',ls='--',lw=1)
    ax.set_xlabel('Ground-truth F0 (Hz)');ax.set_ylabel('Estimated F0 (Hz)');ax.set_title('Synthetic periodic signals: F0 agreement')
    selected=data[(data.measure.isin(['dc_cycles','dd_m','de_j_m3','dr_j']))&(data.role=='acceptance')]
    groups=list(selected.groupby('measure',sort=False))
    for i,(name,group) in enumerate(groups):
        axs[1].scatter(np.full(len(group),i),group.relative_error*100,s=25,alpha=.8,label=name)
    axs[1].set_xticks(range(len(groups)),[g[0] for g in groups],rotation=15)
    axs[1].set_ylabel('Absolute relative error (%)');axs[1].set_title('Independent model-dose reference')
    axs[1].axhline(2,color='#C84E71',ls='--',lw=1,label='2% dose criterion')
    for ax in axs:ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('VoxDose 2.0 | Numerical validation - synthetic ground truth',fontsize=13,fontweight='bold',color='#20354A')
    fig.savefig(OUT/'ground_truth_validation.png',dpi=180)
    fig.savefig(OUT/'ground_truth_validation.svg')
    fig.clear()

if __name__=='__main__':main()
