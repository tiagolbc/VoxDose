import math,threading,copy,zipfile,json,io
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import soundfile as sf
from scipy import signal
from voxdose.core import (Config,analyze,calibrate,Cancelled,distance_correction,
    summarize,frame_doses,_model_integrands,a_sos,a_weighting_db,compatibility,window_summary)
from voxdose.storage import save_session,load_session,export_tables

def frames(duration=2,step=.05,f0=200,spl=75,voiced=True):
    starts=np.arange(0,duration,step);w=np.minimum(step,duration-starts)
    return pd.DataFrame({'time_s':starts,'center_s':starts+w/2,'dt_s':w,'rms_dbfs':-20.,'spl_z_db':spl,
        'spl_a_db':spl-5,'level_db':spl-5,'f0_hz':f0 if voiced else np.nan,'voiced':voiced,'clipping_fraction':0.})

def acoustic():return pd.DataFrame(columns=['start_s','end_s','voiced_fraction','cpps_db','hnr_db'])

@pytest.fixture
def tone(tmp_path):
    def make(name='tone.wav',freq=200,amplitude=.1,seconds=3,fs=16000,channels=1):
        t=np.arange(round(seconds*fs))/fs
        x=amplitude*(np.sin(2*np.pi*freq*t)+.3*np.sin(4*np.pi*freq*t))
        if channels==2:x=np.column_stack((x,np.sin(2*np.pi*300*t)*amplitude))
        p=tmp_path/name;sf.write(p,x,fs,subtype='FLOAT');return p
    return make

def test_analytic_time_and_cycles():
    s=summarize(frames(),acoustic(),Config())
    assert s['dt_s']==pytest.approx(2)
    assert s['dc_cycles']==pytest.approx(400)
    assert s['vli_kcycles']==pytest.approx(.4)
    assert s['dt_pct']==pytest.approx(100)

@pytest.mark.parametrize('step',[.01,.025,.05,.1,.2])
def test_doses_do_not_depend_on_analysis_step(step):
    s=summarize(frames(step=step),acoustic(),Config())
    reference=summarize(frames(step=.05),acoustic(),Config())
    for k in ['dt_s','dc_cycles','dd_m','de_j_m3','dr_j']:
        assert s[k]==pytest.approx(reference[k],rel=1e-12)

def test_titze_equations_independent_scalar_reference():
    # Hand-evaluated equations 14-24 at 120 Hz, SPL=78.5 dB @50cm.
    f=120.;pth=.20;excess=1.;A=.05*.016*math.sqrt(excess/pth)
    T=.0158/(1+2.15);eta=5.4/f
    dd,de,dr=_model_integrands(np.array([f]),np.array([78.5]),'male')
    assert dd[0]==pytest.approx(4*A*f)
    assert de[0]==pytest.approx(.5*eta*(A/T)**2*(2*math.pi*f)**2)
    assert dr[0]==pytest.approx(4*math.pi*.5**2*10**((78.5-120)/10))

def test_average_model_means_doses():
    m=_model_integrands(np.array([200.]),np.array([75.]),'male')
    f=_model_integrands(np.array([200.]),np.array([75.]),'female')
    avg=_model_integrands(np.array([200.]),np.array([75.]),'average')
    assert np.allclose(avg,(np.array(m)+np.array(f))/2)

def test_distance_sign_and_dose_invariance():
    assert distance_correction(80,.3,.5)==pytest.approx(75.5630250077)
    assert distance_correction(80,.5,1)==pytest.approx(73.9794000867)
    a=frames(spl=80);b=frames(spl=float(distance_correction(80,.3,.5)))
    sa=summarize(a,acoustic(),Config(target_distance_m=.3));sb=summarize(b,acoustic(),Config(target_distance_m=.5))
    for k in ['dd_m','de_j_m3','dr_j']:assert sa[k]==pytest.approx(sb[k])

def test_energy_mean_is_not_arithmetic():
    f=frames();f.loc[f.index[:20],'spl_z_db']=60;f.loc[f.index[20:],'spl_z_db']=80
    s=summarize(f,acoustic(),Config())
    assert s['spl_z_mean']==pytest.approx(70)
    assert s['spl_z_leq']==pytest.approx(10*math.log10((10**6+10**8)/2))
    assert s['spl_z_sd']==pytest.approx(10)

def test_partial_frame_and_interval_integration():
    f=frames(duration=1.023)
    s=summarize(f,acoustic(),Config(),.037,.986)
    assert s['duration_s']==pytest.approx(.949)
    assert s['dt_s']==pytest.approx(.949)
    assert s['dc_cycles']==pytest.approx(.949*200)

def test_pauses_and_silence():
    f=frames(duration=10);f.loc[:99,'voiced']=False;f.loc[:99,'f0_hz']=np.nan
    s=summarize(f,acoustic(),Config())
    assert s['dt_s']==pytest.approx(5)
    assert s['dt_pct']==pytest.approx(50)
    assert s['long_pause_count']==1
    assert s['max_pause_s']==pytest.approx(5)
    assert s['max_bout_s']==pytest.approx(5)
    quiet=summarize(frames(voiced=False),acoustic(),Config())
    assert quiet['dt_s']==0 and quiet['f0_mean'] is None and quiet['dd_m']==0

def test_missing_spl_never_generates_physical_doses():
    f=frames();f['spl_z_db']=np.nan;f['spl_a_db']=np.nan
    s=summarize(f,acoustic(),Config())
    assert all(s[k] is None for k in ['dd_m','de_j_m3','dr_j'])
    assert s['dc_cycles']>0

def test_digital_a_filter_response():
    fs=48000;sos=a_sos(fs)
    _,h=signal.sosfreqz(sos,worN=np.array([100.,1000.,4000.]),fs=fs)
    response=20*np.log10(abs(h))
    assert response[1]==pytest.approx(0,abs=1e-10)
    assert np.allclose(response,a_weighting_db([100,1000,4000]),atol=.2)

@pytest.mark.parametrize('fs',[8000,11025,16000,44100,48000])
def test_frame_axis_covers_entire_audio_without_drift(tone,fs):
    p=tone(fs=fs,seconds=1.123)
    r=analyze(p,Config(cpps=False))
    assert len(r.frames)==math.ceil(sf.info(p).duration/.05)
    assert r.frames.dt_s.sum()==pytest.approx(sf.info(p).duration)
    assert (r.frames.time_s+r.frames.dt_s).iloc[-1]==pytest.approx(sf.info(p).duration)
    assert np.max(abs(r.frames.time_s-np.arange(len(r.frames))*.05))<=.51/fs

def test_pitch_and_explicit_channel(tone):
    p=tone(channels=2)
    a=analyze(p,Config(channel=0,cpps=False));b=analyze(p,Config(channel=1,cpps=False))
    assert a.summary['f0_mean']==pytest.approx(200,abs=1)
    assert b.summary['f0_mean']==pytest.approx(300,abs=1)

def test_air_calibration_matches_known_level(tone):
    p=tone(freq=1000)
    cfg=Config(f0_min=60,f0_max=1200,calibration=[{'path':str(p),'level':80}],calibration_weighting='A',
               calibration_distance_m=.5,target_distance_m=.5,cpps=False)
    r=analyze(p,cfg)
    assert r.summary['spl_a_mean']==pytest.approx(80,abs=.03)
    assert r.summary['dd_m']>0

def test_contact_three_point_regression_and_a_restriction(tone):
    paths=[tone(name=f'cal{i}.wav',amplitude=a) for i,a in enumerate([.02,.06324555,.2])]
    pts=[{'path':str(p),'level':level} for p,level in zip(paths,[60,70,80])]
    cfg=Config(sensor='contact',calibration=pts,cpps=False)
    c=calibrate(cfg)
    assert c['slope']==pytest.approx(1,abs=.001)
    assert c['rmse_db']<.001
    r=analyze(paths[1],cfg)
    assert r.summary['spl_a_mean'] is not None
    assert r.summary['spl_z_mean'] is None and r.summary['dd_m'] is None

def test_reject_silent_calibration_and_insufficient_contact(tone):
    p=tone(amplitude=0)
    with pytest.raises(ValueError):calibrate(Config(calibration=[{'path':str(p),'level':80}]))
    p=tone()
    with pytest.raises(ValueError):calibrate(Config(sensor='contact',calibration=[{'path':str(p),'level':80}]))

def test_cancelled_before_read(tone):
    event=threading.Event();event.set()
    with pytest.raises(Cancelled):analyze(tone(),Config(),cancel=event)

def test_cpp_sensible_and_once_per_window(tone):
    r=analyze(tone(seconds=12.1),Config(cpps=True))
    assert len(r.acoustic)==3
    assert r.acoustic.cpps_db.notna().all()
    assert r.summary['cpps_db']>5
    assert r.summary['hnr_db']>5

def test_a_filter_tail_cannot_voice_digital_silence(tone,tmp_path):
    fs=16000;t=np.arange(fs*3)/fs;voice=.02*np.sin(2*np.pi*200*t)
    cal=tmp_path/'cal_z.wav';sf.write(cal,voice,fs,subtype='FLOAT')
    path=tmp_path/'voice_then_silence.wav';sf.write(path,np.r_[np.zeros(fs),voice,np.zeros(fs)],fs,subtype='FLOAT')
    cfg=Config(f0_min=40,f0_max=600,calibration=[{'path':str(cal),'level':75}],
               calibration_weighting='Z',calibration_distance_m=.5,target_distance_m=.5,gate_spl=20,cpps=False)
    r=analyze(path,cfg)
    zero=r.frames.rms_dbfs<=-299
    assert not r.frames.loc[zero,'voiced'].any()

def test_chunk_boundary_stability(tone):
    p=tone(seconds=65,fs=11025)
    a=analyze(p,Config(chunk_s=10,cpps=False));b=analyze(p,Config(chunk_s=30,cpps=False))
    assert len(a.frames)==len(b.frames)==1300
    assert np.allclose(a.frames.time_s,b.frames.time_s)
    assert a.summary['dc_cycles']==pytest.approx(b.summary['dc_cycles'],rel=.0001)
    assert a.metadata['selected_pcm_sha256']==b.metadata['selected_pcm_sha256']

def test_portable_roundtrip_and_excel(tone,tmp_path):
    r=analyze(tone(),Config(cpps=False,subject='P001',task='reading',device='test'))
    r.metadata['diary']=[{'effort':3}]
    p=save_session(r,tmp_path/'session.voxdose');loaded=load_session(p)
    assert loaded.summary['dc_cycles']==pytest.approx(r.summary['dc_cycles'])
    assert loaded.summary['dd_m'] is None
    assert loaded.metadata['diary']==[{'effort':3}]
    export_tables(loaded,tmp_path/'export')
    from openpyxl import load_workbook
    w=load_workbook(tmp_path/'export'/'VoxDose_results.xlsx')
    assert set(w.sheetnames)=={'Summary','Windows','Acoustic_5s','Metadata','Quality'}
    assert w['Summary'].freeze_panes=='A2'

def test_compatibility_and_rate_normalization(tone):
    cfg=Config(cpps=False,subject='P001',task='reading',device='setup1')
    a=analyze(tone(seconds=10),cfg);b=analyze(tone(name='long.wav',seconds=20),cfg)
    assert not compatibility(a,b)
    assert a.summary['dc_cycles_per_hour']==pytest.approx(b.summary['dc_cycles_per_hour'],rel=.02)
    b.metadata['config']['task']='singing';assert 'task' in compatibility(a,b)
    b.metadata['config']['task']='reading';b.metadata['config']['subject']='';assert 'subject' in compatibility(a,b)

def test_large_frame_table_four_hours():
    f=frames(duration=4*3600)
    s=summarize(f,acoustic(),Config())
    assert len(f)==288000
    assert s['dt_s']==pytest.approx(14400)
    assert s['dc_cycles']==pytest.approx(2_880_000)
    assert s['dt_pct']<=100.0000001

@pytest.mark.parametrize('kwargs',[{'f0_min':600,'f0_max':500},{'target_distance_m':0},{'f0_min':float('nan')},{'channel':-1},{'chunk_s':17}])
def test_configuration_validation(kwargs):
    with pytest.raises(ValueError):Config(**kwargs).validate()
