"""Portable, non-executable session files and transparent tabular exports."""
from __future__ import annotations
from pathlib import Path
from dataclasses import fields
from datetime import datetime
import io,json,zipfile,uuid,re,os,math,sys
import numpy as np
import pandas as pd
from .core import Result,Config,SCHEMA,summarize,window_summary
from .i18n import metric,METRICS

BASE = Path(__file__).resolve().parents[1]
RESOURCES=BASE
def data_directory(resources,executable,frozen,platform,environ,home):
    if environ.get('VOXDOSE_DATA_DIR'):
        return Path(environ['VOXDOSE_DATA_DIR']).resolve()
    if not frozen:return Path(resources)
    executable_folder=Path(executable).resolve().parent
    if platform=='darwin':return Path(home)/'Library'/'Application Support'/'VoxDose'
    if platform=='win32' and (executable_folder/'installed.flag').is_file():
        return Path(environ.get('LOCALAPPDATA',str(Path(home)/'AppData'/'Local')))/'VoxDose'
    return executable_folder

BASE=data_directory(RESOURCES,sys.executable,getattr(sys,'frozen',False),sys.platform,os.environ,Path.home())
if os.environ.get('VOXDOSE_DATA_DIR'):
    BASE=Path(os.environ['VOXDOSE_DATA_DIR']).resolve()
OUTPUT=BASE/'results'

def clean_json(value):
    if isinstance(value,dict):return {str(k):clean_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean_json(v) for v in value]
    if isinstance(value,(np.floating,float)):return float(value) if math.isfinite(value) else None
    if isinstance(value,np.integer):return int(value)
    if isinstance(value,np.bool_):return bool(value)
    return value

def json_text(value):return json.dumps(clean_json(value),ensure_ascii=False,indent=2,allow_nan=False)

def save_session(result:Result,path:Path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.writestr('manifest.json',json_text({'metadata':result.metadata,'summary':result.summary,'warnings':result.warnings}))
            for name,df in [('frames',result.frames),('acoustic',result.acoustic),('windows',result.windows)]:
                with z.open(name+'.csv','w') as raw:
                    with io.TextIOWrapper(raw,encoding='utf-8',newline='') as f:df.to_csv(f,index=False)
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()
    return path

def load_session(path:Path):
    with zipfile.ZipFile(path) as z:
        wanted={'manifest.json','frames.csv','acoustic.csv','windows.csv'}
        if not wanted.issubset(z.namelist()):raise ValueError('Invalid VoxDose session.')
        if sum(i.file_size for i in z.infolist())>2_000_000_000:raise ValueError('Session exceeds 2 GB safety limit.')
        info=json.loads(z.read('manifest.json'))
        meta=info['metadata']
        if meta.get('schema')!=SCHEMA:raise ValueError('Unsupported session version.')
        allowed={f.name for f in fields(Config)}
        cfg=Config(**{k:v for k,v in meta['config'].items() if k in allowed});cfg.validate()
        df=pd.read_csv(z.open('frames.csv'));ac=pd.read_csv(z.open('acoustic.csv'))
        required={'time_s','center_s','dt_s','voiced','f0_hz','level_db','spl_z_db','spl_a_db','clipping_fraction','rms_dbfs'}
        if not required.issubset(df.columns) or df.empty:raise ValueError('Invalid session frame table.')
        for col in required-{'voiced'}:df[col]=pd.to_numeric(df[col],errors='raise')
        if df.voiced.dtype!=bool:
            if not df.voiced.isin([True,False,0,1,'True','False']).all():raise ValueError('Invalid voicing flags.')
            df.voiced=df.voiced.map(lambda v:v in [True,1,'True'])
        if (df.dt_s<=0).any() or not np.isfinite(df[['time_s','center_s','dt_s','rms_dbfs']]).all().all():raise ValueError('Invalid frame durations.')
        if (df.time_s.diff().dropna()<=0).any() or df.time_s.iloc[0]<0:raise ValueError('Invalid time axis.')
        if not np.allclose(df.time_s.to_numpy()[1:],(df.time_s+df.dt_s).to_numpy()[:-1],atol=1e-6):raise ValueError('Session has time gaps/overlaps.')
        if not np.isclose(df.dt_s.sum(),meta['duration_s'],atol=1e-5):raise ValueError('Session duration mismatch.')
        if not {'start_s','end_s','voiced_fraction','cpps_db','hnr_db'}.issubset(ac.columns):raise ValueError('Invalid acoustic windows.')
        # Recompute summaries rather than trusting edited cached values.
        return Result(meta,df,ac,summarize(df,ac,cfg),window_summary(df,ac,cfg),info.get('warnings',[]))

def _excel_safe(s):
    s=str(s)
    return "'"+s if s.startswith(('=','+','-','@')) else s

def export_tables(result:Result,folder:Path,language='pt_BR'):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    result.frames.to_csv(folder/'frames.csv.gz',index=False,compression='gzip')
    result.acoustic.to_csv(folder/'acoustic_5s.csv',index=False)
    result.windows.to_csv(folder/'windows.csv',index=False)
    (folder/'metadata.json').write_text(json_text(result.metadata),encoding='utf-8')
    rows=[]
    for key in METRICS:
        if key in result.summary:
            label,unit,explain=metric(key,language)
            rows.append([key,label,result.summary[key],unit,explain])
    summary=pd.DataFrame(rows,columns=['id','Medida / Measure','Valor / Value','Unidade / Unit','Descrição / Description'])
    summary.to_csv(folder/'summary.csv',index=False,encoding='utf-8-sig')
    with pd.ExcelWriter(folder/'VoxDose_results.xlsx',engine='openpyxl') as writer:
        summary.to_excel(writer,sheet_name='Summary',index=False)
        # Avoid Excel's row limit for arbitrarily long analyses.
        for name,data in [('Windows',result.windows),('Acoustic_5s',result.acoustic)]:
            for start in range(0,max(1,len(data)),1_000_000):
                data.iloc[start:start+1_000_000].to_excel(writer,sheet_name=name if start==0 else f'{name}_{start//1_000_000+1}',index=False)
        meta=pd.DataFrame([(k,_excel_safe(json_text(v) if isinstance(v,(dict,list)) else v)) for k,v in result.metadata.items()],columns=['Key','Value'])
        meta.to_excel(writer,sheet_name='Metadata',index=False)
        pd.DataFrame({'quality_flags':result.warnings}).to_excel(writer,sheet_name='Quality',index=False)
        from openpyxl.styles import Font,PatternFill,Alignment
        for ws in writer.book:
            ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions;ws.row_dimensions[1].height=30
            for cell in ws[1]:
                cell.font=Font(name='Calibri',bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='087F8C')
                cell.alignment=Alignment(vertical='center',wrap_text=True)
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font=Font(name='Calibri',size=11,color='20354A')
                    if cell.row%2==0:cell.fill=PatternFill('solid',fgColor='F0F7F8')
                    if cell.data_type=='n':cell.number_format='0.000'
            for col in ws.columns:
                letter=col[0].column_letter;ws.column_dimensions[letter].width=min(64,max(16,max(len(str(c.value or '')) for c in list(col)[:100])+2))
        writer.book['Summary'].column_dimensions['E'].width=90
        for row in writer.book['Summary'].iter_rows(min_row=2):
            row[4].alignment=Alignment(wrap_text=True,vertical='center')
            writer.book['Summary'].row_dimensions[row[0].row].height=36
    from .plots import export_summary_table
    export_summary_table(result,folder,language)
    return folder

def new_output_folder(result):
    name=re.sub(r'[^\w .-]','_',result.label)[:70]
    path=OUTPUT/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+name+'_'+uuid.uuid4().hex[:6])
    path.mkdir(parents=True,exist_ok=False)
    return path
