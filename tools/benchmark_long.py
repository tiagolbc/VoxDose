"""Generate and stream two hours of synthetic audio without loading it all."""
import sys,time,json,threading
from pathlib import Path
import numpy as np
import soundfile as sf
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from voxdose.core import Config,analyze
from voxdose.storage import save_session
root=Path(__file__).resolve().parents[1];out=root/'validation'/'long_audio';out.mkdir(parents=True,exist_ok=True)
path=out/'synthetic_2h.flac';fs=16000
t=np.arange(fs*10)/fs
block=.08*np.sin(2*np.pi*180*t)*(np.mod(t,10)<4)
with sf.SoundFile(path,'w',samplerate=fs,channels=1,format='FLAC',subtype='PCM_16') as f:
    for _ in range(720):f.write(block)
process=psutil.Process();peak=[process.memory_info().rss];done=threading.Event()
def sample():
    while not done.wait(.1):peak[0]=max(peak[0],process.memory_info().rss)
thread=threading.Thread(target=sample,daemon=True);thread.start();start=time.perf_counter()
cfg=Config(cpps=False,subject='SYNTHETIC',task='180Hz_4s_on_6s_off',device='generated')
r=analyze(path,cfg);elapsed=time.perf_counter()-start;done.set();thread.join()
save_session(r,out/'session.voxdose')
stats={'duration_s':r.metadata['duration_s'],'frames':len(r.frames),'wall_seconds':elapsed,'sampled_peak_rss_mb':peak[0]/2**20,
       'audio_file_mb':path.stat().st_size/2**20,'summary':r.summary,'cpps_enabled':False,
       'limitation':'Synthetic functional/performance check, not a clinical or natural-speech validation.'}
(out/'benchmark.json').write_text(json.dumps(stats,indent=2),encoding='utf-8');print(json.dumps(stats,indent=2))
