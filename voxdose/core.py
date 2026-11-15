"""Streaming, timestamp-aligned acoustic analysis. No GUI or file export side effects.

Development: Tiago Lima Bicalho Cruz - Universidade Federal de Minas Gerais.
Dose equations adapted from Pasquale Bottalico's MATLAB DOSI.m and checked
against Titze et al. (2003), equations 14-24. See docs/METHODS.md.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
import hashlib, math, platform, threading
import numpy as np
import pandas as pd
import soundfile as sf
import parselmouth
from scipy import signal
from . import __version__, AUTHOR, AFFILIATION

STEP = 0.05
SCHEMA = 2

class Cancelled(Exception):
    pass

@dataclass
class CalibrationPoint:
    path: str
    level: float

@dataclass
class Config:
    sensor: str = 'air'
    channel: int = 0
    f0_min: float = 60.0
    f0_max: float = 500.0
    model: str = 'average'
    calibration: list[dict] = field(default_factory=list)
    calibration_weighting: str = 'A'
    calibration_distance_m: float = .30
    target_distance_m: float = .50
    gate_dbfs: float = -45.0
    gate_spl: float = 45.0
    window_s: float = 60.0
    cpps: bool = True
    chunk_s: float = 30.0
    subject: str = ''
    task: str = ''
    device: str = ''
    notes: str = ''

    def validate(self):
        numeric = [self.f0_min,self.f0_max,self.calibration_distance_m,self.target_distance_m,
                   self.gate_dbfs,self.gate_spl,self.window_s,self.chunk_s]
        if not all(math.isfinite(x) for x in numeric):
            raise ValueError('All settings must be finite / Todos os parâmetros devem ser finitos.')
        if not (30 <= self.f0_min < self.f0_max <= 2000):
            raise ValueError('F0: require 30 <= minimum < maximum <= 2000 Hz.')
        if self.sensor not in {'air','contact','accelerometer'} or self.model not in {'male','female','average'}:
            raise ValueError('Invalid sensor/model / Sensor ou modelo inválido.')
        if self.calibration_weighting not in {'A','Z'} or not (0.01 <= self.calibration_distance_m <= 10 and .01 <= self.target_distance_m <= 10):
            raise ValueError('Invalid weighting or distance / Ponderação ou distância inválida.')
        if not (5 <= self.chunk_s <= 300 and self.chunk_s % 5 == 0 and 5 <= self.window_s <= 3600):
            raise ValueError('Chunks must be multiples of 5 s; trend windows 5-3600 s.')
        if not (isinstance(self.channel,int) and self.channel >= 0 and -120 <= self.gate_dbfs <= 0 and 0 <= self.gate_spl <= 140):
            raise ValueError('Invalid channel or gate / Canal ou limiar inválido.')
        for p in self.calibration:
            if not math.isfinite(float(p['level'])) or not 20 <= float(p['level']) <= 140:
                raise ValueError('Calibration level outside 20-140 dB.')

@dataclass
class Result:
    metadata: dict
    frames: pd.DataFrame
    acoustic: pd.DataFrame
    summary: dict
    windows: pd.DataFrame
    warnings: list[str] = field(default_factory=list)

    @property
    def label(self):
        return self.metadata.get('label') or Path(self.metadata['source']).stem

def a_weighting_db(f):
    """Nominal analog A response (normalized to 0 dB at 1 kHz)."""
    f = np.asarray(f,dtype=float)
    q = f*f
    den = (q+20.6**2)*np.sqrt((q+107.7**2)*(q+737.9**2))*(q+12194.0**2)
    r = np.divide(12194.0**2*q*q,den,out=np.zeros_like(q),where=den>0)
    return 20*np.log10(np.maximum(r,1e-30))+2.0

def a_sos(fs):
    f1,f2,f3,f4 = 20.598997,107.65265,737.86223,12194.217
    z = np.zeros(4)
    p = -2*np.pi*np.array([f1,f1,f2,f3,f4,f4])
    k = (2*np.pi*f4)**2 * 10**(1.9997/20)
    zd,pd,kd = signal.bilinear_zpk(z,p,k,fs)
    sos=signal.zpk2sos(zd,pd,kd)
    # Normalize digital response at 1 kHz. High-frequency bilinear warping is documented.
    _,h=signal.sosfreqz(sos,worN=[1000],fs=fs)
    sos[0,:3] /= abs(h[0])
    return sos

def db_rms(x):
    return float(10*np.log10(max(float(np.mean(np.square(x))),1e-30)))

def distance_correction(db, source_m, target_m):
    if min(source_m,target_m)<=0:
        raise ValueError('Distances must be positive.')
    return np.asarray(db)+20*np.log10(source_m/target_m)

def _check_cancel(event):
    if event is not None and event.is_set():
        raise Cancelled('Cancelled / Cancelado')

def calibrate(cfg:Config, cancel=None):
    cfg.validate()
    if not cfg.calibration:
        return {'kind':'none','offset':None,'slope':None,'points':[],'weighting':cfg.calibration_weighting}
    pts=[]
    for p in cfg.calibration:
        _check_cancel(cancel)
        with sf.SoundFile(p['path']) as f:
            if cfg.channel>=f.channels:
                raise ValueError('Calibration channel not available / Canal ausente na calibração.')
            sos=a_sos(f.samplerate) if cfg.sensor=='air' and cfg.calibration_weighting=='A' else None
            state=np.zeros((len(sos),2)) if sos is not None else None
            energy=0.; n=0; clips=0
            for block in f.blocks(blocksize=f.samplerate*10,always_2d=True,dtype='float64'):
                _check_cancel(cancel)
                x=block[:,cfg.channel]; clips+=int(np.count_nonzero(abs(x)>=.999))
                if sos is not None:
                    x,state=signal.sosfilt(sos,x,zi=state)
                energy+=float(np.dot(x,x)); n+=len(x)
            if n < .2*f.samplerate or energy/n<1e-14:
                raise ValueError('Calibration is silent/too short / Calibração silenciosa ou curta.')
            if clips/n > .001:
                raise ValueError('Calibration clipping >0.1%; record again / Regrave a calibração saturada.')
            pts.append({'path':str(Path(p['path']).resolve()),'digital_db':10*np.log10(energy/n),
                        'reference_db':float(p['level']),'sample_rate':f.samplerate,'channel':cfg.channel})
    x=np.array([p['digital_db'] for p in pts]); y=np.array([p['reference_db'] for p in pts])
    if cfg.sensor=='air':
        slope=1.; offset=float(np.mean(y-x)); kind='air_scalar'
    else:
        if len(pts)<3 or np.ptp(x)<10 or np.ptp(y)<10:
            raise ValueError('Contact/ACC requires >=3 calibration levels spanning >=10 dB / Use 3 níveis com amplitude >=10 dB.')
        slope,offset=np.polyfit(x,y,1); kind='contact_regression_experimental'
        if not .1<slope<5:
            raise ValueError('Invalid contact calibration slope / Inclinação de calibração inválida.')
    resid=y-(slope*x+offset)
    return {'kind':kind,'offset':float(offset),'slope':float(slope),'points':pts,
            'rmse_db':float(np.sqrt(np.mean(resid**2))),
            'r2':float(1-np.sum(resid**2)/np.sum((y-y.mean())**2)) if np.ptp(y)>0 else None,
            'weighting':cfg.calibration_weighting}

def _nearest_pitch(x,fs,centers,cfg,origin):
    if len(x)/fs < 3/cfg.f0_min:
        return np.zeros(len(centers))
    snd=parselmouth.Sound(x,sampling_frequency=fs)
    pitch=snd.to_pitch_ac(time_step=STEP,pitch_floor=cfg.f0_min,pitch_ceiling=cfg.f0_max,
                          voicing_threshold=.45,very_accurate=False)
    tt=pitch.xs()+origin; hz=pitch.selected_array['frequency']
    idx=np.searchsorted(tt,centers).clip(0,len(tt)-1)
    prev=np.maximum(0,idx-1)
    idx=np.where(abs(tt[prev]-centers)<abs(tt[idx]-centers),prev,idx)
    out=hz[idx].copy()
    out[(abs(tt[idx]-centers)>STEP*.51)|(out<cfg.f0_min)|(out>cfg.f0_max)]=0
    return out

def cpps_hnr(x,fs,cfg):
    snd=parselmouth.Sound(x,sampling_frequency=fs)
    pcg=parselmouth.praat.call(snd,'To PowerCepstrogram',60.,.002,min(5000.,fs/2),50.)
    cp=parselmouth.praat.call(pcg,'Get CPPS',False,.01,.001,cfg.f0_min,cfg.f0_max,
                            .05,'Parabolic',.001,0.,'Straight','Robust')
    hm=snd.to_harmonicity_ac(time_step=.01,minimum_pitch=cfg.f0_min)
    hn=hm.values.ravel(); hn=hn[(hn>-100)&np.isfinite(hn)]
    return float(cp),float(np.mean(hn)) if len(hn) else np.nan

def _model_integrands(f0,spl50,model):
    """Return distance velocity, dissipated power density, radiated power at 0.5 m.

    0.05*L0 is the empirical amplitude coefficient, NOT a time step.
    eta in Pa.s, A and T in metres -> De in J/m3. No unexplained 1000 factor.
    """
    f=np.maximum(f0,1e-12)
    def branch(sex):
        nom,L0,T0,b,k = (120.,.016,.0158,2.15,5.4) if sex=='male' else (190.,.010,.01063,1.69,1.4)
        pth=.14+.06*(f/nom)**2
        excess=10**((spl50-78.5)/27.3)
        amplitude=.05*L0*np.sqrt(excess/pth)
        thickness=T0/(1+b*np.sqrt(f/nom))
        dd=4*amplitude*f
        de=.5*(k/f)*(amplitude/thickness)**2*(2*np.pi*f)**2
        return dd,de
    if model=='average':
        m=branch('male'); w=branch('female')
        dd,de=(m[0]+w[0])/2,(m[1]+w[1])/2
    else:
        dd,de=branch(model)
    dr=4*np.pi*.5**2*10**((spl50-120)/10)
    return dd,de,dr

def frame_doses(frames,cfg):
    w=frames['dt_s'].to_numpy(); v=frames['voiced'].to_numpy(dtype=bool)
    f0=frames['f0_hz'].fillna(0).to_numpy()
    dt=w*v; dc=dt*f0
    has=frames['spl_z_db'].notna().any()
    if has:
        spl50=distance_correction(frames['spl_z_db'].to_numpy(),cfg.target_distance_m,.5)
        dd,de,dr=_model_integrands(f0,np.nan_to_num(spl50,nan=0.),cfg.model)
        dd,de,dr=dd*dt,de*dt,dr*dt
    else:
        dd=de=dr=np.full(len(w),np.nan)
    return pd.DataFrame({'dt_dose_s':dt,'cycles':dc,'dd_m':dd,'de_j_m3':de,'dr_j':dr},index=frames.index)

def weighted_mean(x,w):
    x=np.asarray(x);w=np.asarray(w); mask=np.isfinite(x)&(w>0)
    return float(np.average(x[mask],weights=w[mask])) if mask.any() else None

def weighted_quantile(x,w,q):
    x=np.asarray(x);w=np.asarray(w);mask=np.isfinite(x)&(w>0)
    if not mask.any():return None
    x,w=x[mask],w[mask]; order=np.argsort(x);x,w=x[order],w[order]
    return float(np.interp(q,(np.cumsum(w)-.5*w)/w.sum(),x))

def _runs(mask,weights):
    if not len(mask):return np.array([]),np.array([],dtype=bool)
    starts=np.r_[0,np.flatnonzero(mask[1:]!=mask[:-1])+1]
    return np.add.reduceat(weights,starts),mask[starts]

def summarize(frames,acoustic,cfg,start=None,end=None):
    f=frames.copy()
    if start is not None or end is not None:
        lo=0 if start is None else float(start); hi=np.inf if end is None else float(end)
        f['dt_s']=np.maximum(0,np.minimum(f.time_s+f.dt_s,hi)-np.maximum(f.time_s,lo))
        f=f[f.dt_s>0].copy()
    duration=float(f.dt_s.sum());v=f.voiced.to_numpy(dtype=bool);w=f.dt_s.to_numpy()
    dw=w*v; phon=float(dw.sum()); doses=frame_doses(f,cfg)
    s={'duration_s':duration,'dt_s':phon,'dt_pct':100*phon/duration if duration else 0.,
       'dc_cycles':float(doses.cycles.sum()),'vli_kcycles':float(doses.cycles.sum()/1000),
       'dd_m':None,'de_j_m3':None,'dr_j':None}
    for key in ['dd_m','de_j_m3','dr_j']:
        if doses[key].notna().any():s[key]=float(doses[key].sum())
    for key in ['dc_cycles','dd_m','de_j_m3','dr_j']:
        s[key+'_per_hour']=s[key]*3600/duration if duration and s[key] is not None else None
        s[key+'_per_phonation_s']=s[key]/phon if phon and s[key] is not None else None
    for name,col in [('f0','f0_hz'),('spl_z','spl_z_db'),('spl_a','spl_a_db'),('level','level_db')]:
        x=f[col].to_numpy()
        s[name+'_mean']=weighted_mean(x,dw)
        avg=s[name+'_mean']
        s[name+'_sd']=math.sqrt(weighted_mean((x-avg)**2,dw)) if avg is not None else None
        for p in [10,50,90]:s[name+'_p'+str(p)]=weighted_quantile(x,dw,p/100)
    s['f0_range_st']=12*math.log2(s['f0_p90']/s['f0_p10']) if s['f0_p10'] and s['f0_p90'] else None
    for name in ['spl_z','spl_a','level']:
        val=f[{'spl_z':'spl_z_db','spl_a':'spl_a_db','level':'level_db'}[name]].to_numpy()
        good=np.isfinite(val)&v
        s[name+'_leq']=10*math.log10(float(np.average(10**(val[good]/10),weights=w[good]))) if good.any() else None
    run_d,run_v=_runs(v,w)
    pauses=run_d[~run_v];bouts=run_d[run_v]
    s.update({'pause_s':float(w[~v].sum()),'pause_count':int(np.count_nonzero(pauses>=.25-1e-9)),
              'long_pause_count':int(np.count_nonzero(pauses>=5-1e-9)),
              'max_pause_s':float(max(pauses,default=0)), 'bout_median_s':float(np.median(bouts)) if len(bouts) else 0.,
              'max_bout_s':float(max(bouts,default=0)),
              'clipping_pct':100*weighted_mean(f.clipping_fraction,w) if duration else 0.})
    ac=acoustic.copy()
    if len(ac):
        low=0 if start is None else start; high=np.inf if end is None else end
        ac['weight']=np.maximum(0,np.minimum(ac.end_s,high)-np.maximum(ac.start_s,low))*ac.voiced_fraction
        s['cpps_db']=weighted_mean(ac.cpps_db,ac.weight)
        s['hnr_db']=weighted_mean(ac.hnr_db,ac.weight)
    else:s['cpps_db']=s['hnr_db']=None
    return s

def window_summary(frames,acoustic,cfg):
    if frames.empty:return pd.DataFrame()
    groups=np.floor(frames.time_s/cfg.window_s).astype(int)
    out=[]
    for group,part in frames.groupby(groups,sort=True):
        lo=group*cfg.window_s;hi=min((group+1)*cfg.window_s,float(frames.time_s.iloc[-1]+frames.dt_s.iloc[-1]))
        ac=acoustic[(acoustic.start_s<hi)&(acoustic.end_s>lo)] if len(acoustic) else acoustic
        row=summarize(part,ac,cfg,lo,hi);row.update(start_s=lo,end_s=hi);out.append(row)
    return pd.DataFrame(out)

def analyze(path:str|Path,cfg:Config,progress=None,cancel:threading.Event|None=None):
    cfg.validate();path=Path(path).resolve(); cal=calibrate(cfg,cancel)
    warn=[]
    if cal['kind']=='none':warn.append('uncalibrated')
    if cfg.sensor!='air':warn.append('contact_experimental')
    if cal.get('rmse_db',0)>2:warn.append('calibration_residual')
    if cal.get('kind')=='air_scalar' and len(cal['points'])==1:warn.append('single_point_calibration')
    records=[];ac_records=[];digest=hashlib.sha256()
    with sf.SoundFile(path) as audio:
        fs=audio.samplerate;total=len(audio);channels=audio.channels
        if fs<8000 or cfg.f0_max>=fs/2:
            raise ValueError('Use audio >=8 kHz and pitch ceiling below Nyquist.')
        if cfg.channel>=channels or total<fs*.1:
            raise ValueError('Invalid channel or audio <0.1 s / Canal inválido ou áudio <0,1 s.')
        chunk_n=int(round(cfg.chunk_s*fs))
        sos=a_sos(fs);state=np.zeros((len(sos),2)); context=int(math.ceil(max(.15,3/cfg.f0_min)*fs))
        for pos in range(0,total,chunk_n):
            _check_cancel(cancel)
            n=min(chunk_n,total-pos);audio.seek(pos)
            raw=audio.read(n,always_2d=True,dtype='float64');x=raw[:,cfg.channel]
            if not np.isfinite(x).all():raise ValueError('Audio contains NaN/Inf / Áudio contém valores inválidos.')
            digest.update(x.astype('<f8').tobytes())
            xa,state=signal.sosfilt(sos,x,zi=state)
            # Round absolute 50 ms boundaries, avoiding drift at rates such as 11025 Hz.
            starts=np.rint(np.arange(int(np.ceil(n/fs/STEP)))*STEP*fs).astype(int)
            starts=starts[starts<n];lens=np.diff(np.r_[starts,n])
            centers=(pos+starts+lens/2)/fs
            left=max(0,pos-context);right=min(total,pos+n+context);audio.seek(left)
            extended=audio.read(right-left,always_2d=True,dtype='float64')[:,cfg.channel]
            f0=_nearest_pitch(extended,fs,centers,cfg,left/fs)
            for j,(a,ln) in enumerate(zip(starts,lens)):
                seg=x[a:a+ln];z=db_rms(seg);aw=db_rms(xa[a:a+ln])
                sz=sa=np.nan
                if cal['kind']=='air_scalar':
                    sz=float(distance_correction(z+cal['offset'],cfg.calibration_distance_m,cfg.target_distance_m))
                    sa=float(distance_correction(aw+cal['offset'],cfg.calibration_distance_m,cfg.target_distance_m))
                elif cal['kind']!='none':
                    mapped=float(distance_correction(cal['slope']*z+cal['offset'],cfg.calibration_distance_m,cfg.target_distance_m))
                    if cfg.calibration_weighting=='Z':sz=mapped
                    else:sa=mapped
                level=sa if np.isfinite(sa) else (sz if np.isfinite(sz) else z)
                above=(level>=cfg.gate_spl) if cal['kind']!='none' else z>=cfg.gate_dbfs
                # A filter tail plus pitch context must not create voicing in a
                # genuinely zero-valued frame after a voiced segment.
                voiced=bool(f0[j]>0 and above and np.any(seg!=0))
                records.append((float((pos+a)/fs),float(ln/fs),float(centers[j]),z,sz,sa,float(level),
                                float(f0[j]) if voiced else np.nan,voiced,float(np.mean(abs(seg)>=.999))))
            if cfg.cpps:
                # One independent observation per 5 seconds; no fabricated 20 Hz CPPS track.
                block_frames=records[-len(starts):]
                for a in range(0,n,5*fs):
                    b=min(n,a+5*fs);lo=(pos+a)/fs;hi=(pos+b)/fs
                    vf=[r for r in block_frames if lo<=r[2]<hi]
                    frac=sum(r[1] for r in vf if r[8])/((b-a)/fs)
                    cp=hn=np.nan
                    if b-a>=fs*.2 and frac>=.2:
                        try:cp,hn=cpps_hnr(x[a:b],fs,cfg)
                        except parselmouth.PraatError:warn.append('cpps_failed')
                    ac_records.append((lo,hi,frac,cp,hn))
            if progress:progress(min(99,int(100*(pos+n)/total)),path.name)
    frames=pd.DataFrame(records,columns=['time_s','dt_s','center_s','rms_dbfs','spl_z_db','spl_a_db','level_db','f0_hz','voiced','clipping_fraction'])
    acoustic=pd.DataFrame(ac_records,columns=['start_s','end_s','voiced_fraction','cpps_db','hnr_db'])
    summary=summarize(frames,acoustic,cfg)
    if not summary['dt_s']:warn.append('no_voicing')
    if summary['clipping_pct']>.1:warn.append('clipping')
    if fs<16000:warn.append('low_sample_rate')
    now=datetime.now().astimezone().isoformat(timespec='seconds')
    meta={'schema':SCHEMA,'software':'VoxDose','version':__version__,'author':AUTHOR,'affiliation':AFFILIATION,
          'adapted_from':'Original MATLAB code by Pasquale Bottalico',
          'model_version':'Titze2003-corrected-2.0','source':str(path),'label':path.stem,'created':now,
          'sample_rate':fs,'channels':channels,'sample_count':total,'selected_pcm_sha256':digest.hexdigest(),
          'duration_s':total/fs,'calibration':cal,'config':asdict(cfg),
          'dependencies':{'python':platform.python_version(),'numpy':np.__version__,'parselmouth':parselmouth.__version__,
                          'praat':parselmouth.PRAAT_VERSION,'soundfile':sf.__version__},
          'cpps_protocol':{'window_s':5,'hop_s':5,'pause_removal':False,'minimum_voiced_fraction':.2,
                          'pitch_floor':60,'time_step':.002,'max_frequency':min(5000,fs/2),
                          'preemphasis':50,'subtract_trend':False,'time_average':.01,'quefrency_average':.001,
                          'peak_pitch_min':cfg.f0_min,'peak_pitch_max':cfg.f0_max,'fit':'Robust'}}
    result=Result(meta,frames,acoustic,summary,window_summary(frames,acoustic,cfg),list(dict.fromkeys(warn)))
    if progress:progress(100,path.name)
    return result

def compatibility(a:Result,b:Result):
    """Reasons to withhold direct deltas; never silently pool incompatible recordings."""
    ca=a.metadata['config'];cb=b.metadata['config'];reasons=[]
    for key in ['sensor','model','f0_min','f0_max','gate_dbfs','gate_spl','cpps','channel','target_distance_m']:
        if ca[key]!=cb[key]:reasons.append(key)
    for key in ['subject','task','device']:
        if not ca.get(key) or not cb.get(key) or ca[key]!=cb[key]:reasons.append(key)
    if a.metadata['calibration']['kind']!=b.metadata['calibration']['kind']:reasons.append('calibration')
    if a.metadata['model_version']!=b.metadata['model_version']:reasons.append('model_version')
    if ca.get('calibration_weighting')!=cb.get('calibration_weighting'):reasons.append('calibration_weighting')
    if ca['sensor']!='air':reasons.append('contact_experimental')
    return reasons
