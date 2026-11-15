"""Modern Matplotlib figures shared by the GUI, image export and manuals."""
from pathlib import Path
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends import backend_svg  # Explicit inclusion in frozen exports.
from .core import Config,frame_doses
from .i18n import metric,METRICS,fmt
from . import AUTHOR

PALETTE=['#087F8C','#6757C8','#D7832C','#C84E71','#2878A8','#5B914C','#8B6B4B','#707A8C']
KINDS=['level','f0','cpps','cycles','phonation','distribution','level_distribution','cpps_distribution','hnr','rms','distance','dissipation','radiation']

def L(language,pt,en):return pt if language=='pt_BR' else en

def decorate(ax):
    ax.set_facecolor('#FFFFFF');ax.grid(axis='y',color='#E7EDF2',linewidth=.7)
    ax.set_axisbelow(True)
    for side in ['top','right']:ax.spines[side].set_visible(False)
    for side in ['left','bottom']:ax.spines[side].set_color('#CBD5DF')
    ax.tick_params(colors='#637487',labelsize=8)
    ax.xaxis.label.set_color('#637487');ax.yaxis.label.set_color('#637487')
    ax.title.set_color('#20354A');ax.title.set_fontsize(10);ax.title.set_fontweight('bold')

def thin(x,y,limit=6000):
    """Preserve temporal extrema in each display bin; statistics use all frames."""
    x=np.asarray(x);y=np.asarray(y)
    if len(x)<=limit:return x,y
    width=int(np.ceil(len(x)/(limit/2)));indices=[]
    for i in range(0,len(x),width):
        block=y[i:i+width]
        if np.isfinite(block).any():
            indices.extend(sorted({i+int(np.nanargmin(block)),i+int(np.nanargmax(block))}))
        else:indices.append(i)
    # Keep NaN boundaries so decimation never joins curves across pauses.
    changes=np.flatnonzero(np.isfinite(y[1:])!=np.isfinite(y[:-1]))
    indices=np.unique(np.r_[indices,changes,changes+1]).astype(int)
    return x[indices],y[indices]

def pause_intervals(frames,minimum_s=.5):
    voiced=frames.voiced.to_numpy(dtype=bool)
    if not len(voiced):return []
    starts=np.r_[0,np.flatnonzero(voiced[1:]!=voiced[:-1])+1]
    ends=np.r_[starts[1:],len(voiced)];out=[]
    for a,b in zip(starts,ends):
        if not voiced[a]:
            lo=float(frames.time_s.iloc[a]);hi=float(frames.time_s.iloc[b-1]+frames.dt_s.iloc[b-1])
            if hi-lo>=minimum_s-1e-9:out.append((lo,hi))
    return out

def supported_window_track(result,column):
    """Display means only during actual detected phonation with adequate support.

    This is a plotting rule; it never deletes frames or changes dose totals.
    A window must contain >=0.5 s and >=5% detected phonation.
    """
    f=result.frames;w=result.windows
    if w.empty:return f.center_s.to_numpy(),np.full(len(f),np.nan)
    idx=np.searchsorted(w.end_s.to_numpy(),f.center_s.to_numpy(),side='right').clip(0,len(w)-1)
    support=(w.dt_s.to_numpy()>=.5)&(w.dt_pct.to_numpy()>=5.)
    yy=w[column].to_numpy(dtype=float)[idx].copy()
    yy[~(f.voiced.to_numpy(dtype=bool)&support[idx])]=np.nan
    return f.center_s.to_numpy(),yy

def shade_pauses(ax,result,language):
    for i,(lo,hi) in enumerate(pause_intervals(result.frames)):
        ax.axvspan(lo/60,hi/60,color='#DCE4EB',alpha=.55,lw=0,zorder=0,
            label=L(language,'Sem fonação detectada (≥0,5 s)','No detected voicing (≥0.5 s)') if i==0 else None)

def add_credit(fig,language):
    engine=fig.get_layout_engine()
    if engine is not None and hasattr(engine,'set'):
        engine.set(rect=(0,.04,1,.96))
    fig.text(.015,.004,L(language,'Códigos originais de dosimetria: Pasquale Bottalico · Adaptação e desenvolvimento VoxDose: ',
        'Original dosimetry code: Pasquale Bottalico · VoxDose adaptation and development: ')+AUTHOR+' · UFMG',
        fontsize=6.2,color='#51697B',ha='left',va='bottom')

def level_unit(result):
    cal=result.metadata['calibration'];cfg=result.metadata['config']
    if cal['kind']=='none':return 'dBFS'
    unit='dBA' if result.frames.spl_a_db.notna().any() else 'dB SPL Z'
    return unit+f' @ {cfg["target_distance_m"]*100:g} cm'

def draw_panel(ax,result,kind,language='pt_BR',color=PALETTE[0],compact=False):
    f=result.frames;a=result.acoustic;w=result.windows
    pt=language=='pt_BR'
    time=f.center_s.to_numpy()/60
    xlabel=L(language,'Tempo (min)','Time (min)')
    if kind in {'level','f0','rms'}:
        col={'level':'level_db','f0':'f0_hz','rms':'rms_dbfs'}[kind]
        y=f[col].to_numpy().copy()
        if kind!='rms':y[~f.voiced.to_numpy()]=np.nan
        x,y=thin(time,y)
        if kind!='rms':
            ax.plot(x,y,color=color,alpha=.5,linestyle='none',marker='.',ms=2,
                label=L(language,'Quadros detectados','Detected frames'))
            shade_pauses(ax,result,language)
        else:ax.plot(x,y,color=color,alpha=.6,lw=.75)
        mean_col={'level':'level_mean','f0':'f0_mean'}
        if kind in mean_col and len(w):
            mx,my=supported_window_track(result,mean_col[kind]);mx,my=thin(mx/60,my)
            ax.plot(mx,my,color=color,lw=1.8,label=L(language,'Média: janela com ≥5% e ≥0,5 s de fonação','Mean: window with ≥5% and ≥0.5 s voicing'))
            if not compact:ax.legend(fontsize=6,frameon=False,loc='upper right')
        ax.set_title({'level':L(language,'Intensidade vocal','Vocal intensity'),
                      'f0':L(language,'Frequência fundamental','Fundamental frequency'),
                      'rms':L(language,'Envelope RMS digital','Digital RMS envelope')}[kind],loc='left',pad=10)
        ax.set_ylabel({'level':level_unit(result),'f0':'Hz','rms':'dBFS'}[kind])
    elif kind in {'cpps','hnr'}:
        col=kind+'_db'
        if len(a) and a[col].notna().any():
            xx=(a.start_s+a.end_s).to_numpy()/120;yy=a[col].to_numpy()
            xx,yy=thin(xx,yy);ax.plot(xx,yy,color=color,lw=1.1,marker='.',ms=3,alpha=.85)
        else:ax.text(.5,.5,L(language,'Medida indisponível','Measure unavailable'),transform=ax.transAxes,ha='center',color='#7C8B99')
        ax.set_title(('CPPS' if kind=='cpps' else 'HNR')+L(language,' · janelas de 5 s',' · 5 s windows'),loc='left',pad=10)
        ax.set_ylabel('dB')
    elif kind in {'cycles','distance','dissipation','radiation'}:
        d=frame_doses(f,Config(**result.metadata['config']))
        col,unit,title={'cycles':('cycles','kcycles',L(language,'Ciclos acumulados','Accumulated cycles')),
            'distance':('dd_m','m',L(language,'Distância acumulada · modelo','Accumulated distance · model')),
            'dissipation':('de_j_m3','J/m³',L(language,'Dissipação acumulada · modelo','Accumulated dissipation · model')),
            'radiation':('dr_j','J',L(language,'Energia radiada acumulada · modelo','Accumulated radiation · model'))}[kind]
        if d[col].notna().any():
            cumulative=np.cumsum(d[col])/(1000 if kind=='cycles' else 1)
            xx,yy=thin((f.time_s+f.dt_s)/60,cumulative)
            ax.fill_between(xx,0,yy,color=color,alpha=.10);ax.plot(xx,yy,color=color,lw=1.8)
        else:ax.text(.5,.5,L(language,'Requer SPL Z calibrado','Requires calibrated SPL Z'),transform=ax.transAxes,ha='center',color='#7C8B99')
        ax.set_title(title,loc='left',pad=10);ax.set_ylabel(unit)
    elif kind=='phonation':
        ax.bar((w.start_s+w.end_s)/120,w.dt_pct,width=(w.end_s-w.start_s)/60*.85,color=color,alpha=.8)
        ax.set_ylim(0,100);ax.set_ylabel('%')
        ax.set_title(L(language,'Fonação por janela','Phonation by window'),loc='left',pad=10)
    elif kind in {'distribution','level_distribution','cpps_distribution'}:
        if kind=='cpps_distribution':
            values=a.cpps_db if len(a) else np.array([])
            valid=np.isfinite(values);weights=(a.end_s-a.start_s)*a.voiced_fraction if len(a) else np.array([])
            title=L(language,'Distribuição de CPPS','CPPS distribution');unit='CPPS (dB)'
        else:
            values=f['f0_hz' if kind=='distribution' else 'level_db'];valid=f.voiced&values.notna();weights=f.dt_s
            title=L(language,'Distribuição de F0','F0 distribution') if kind=='distribution' else L(language,'Distribuição de intensidade','Intensity distribution')
            unit='F0 (Hz)' if kind=='distribution' else level_unit(result)
        if np.any(valid):ax.hist(np.asarray(values)[valid],bins=35,weights=np.asarray(weights)[valid],color=color,edgecolor='white',lw=.4,alpha=.85)
        ax.set_title(title,loc='left',pad=10)
        ax.set_xlabel(unit);ax.set_ylabel(L(language,'Fonação (s)','Phonation (s)'));decorate(ax);return
    ax.set_xlabel(xlabel)
    decorate(ax)

def dashboard(result,language='pt_BR',kind=None):
    fig=Figure(figsize=(12,10) if kind is None else (11,6),dpi=110,facecolor='#FFFFFF',layout='constrained')
    kinds=KINDS[:8] if kind is None else [kind]
    axs=fig.subplots(4,2).ravel() if kind is None else [fig.subplots()]
    for i,(ax,k) in enumerate(zip(axs,kinds)):draw_panel(ax,result,k,language,PALETTE[i%len(PALETTE)],compact=kind is None)
    fig.suptitle('VoxDose 2.0  /  '+result.label,color='#20354A',fontsize=12,fontweight='bold',x=.02,ha='left')
    add_credit(fig,language)
    return fig

def comparison(results,language='pt_BR',relative=False):
    fig=Figure(figsize=(12,7.5),dpi=110,facecolor='white',layout='constrained')
    axs=fig.subplots(2,2).ravel()
    labels=[L(language,'F0 média por janela','Mean F0 by window'),L(language,'Fonação por janela','Phonation by window'),
            L(language,'CPPS por janela de 5 s','CPPS by 5 s window'),L(language,'Ciclos acumulados','Accumulated cycles')]
    for i,r in enumerate(results):
        color=PALETTE[i%len(PALETTE)];w=r.windows;f=r.frames;a=r.acoustic
        scale=100/r.metadata['duration_s'] if relative else 1/60
        xx=(w.start_s+w.end_s)/2*scale
        mx,my=supported_window_track(r,'f0_mean');mx,my=thin(mx*scale,my)
        axs[0].plot(mx,my,label=r.label,color=color,lw=1.8)
        axs[1].plot(xx,w.dt_pct,label=r.label,color=color,lw=1.8)
        if len(a):
            x,y=thin((a.start_s+a.end_s)/2*scale,a.cpps_db)
            axs[2].plot(x,y,label=r.label,color=color,lw=1,alpha=.8)
        d=frame_doses(f,Config(**r.metadata['config']))
        x,y=thin((f.time_s+f.dt_s)*scale,np.cumsum(d.cycles)/1000)
        axs[3].plot(x,y,label=r.label,color=color,lw=1.8)
    for ax,title,unit in zip(axs,labels,['Hz','%','dB','kcycles']):
        ax.set_title(title,loc='left',pad=10);ax.set_ylabel(unit)
        ax.set_xlabel(L(language,'Duração relativa (%)','Relative duration (%)') if relative else L(language,'Tempo (min)','Time (min)'))
        decorate(ax)
        if ax.lines:ax.legend(fontsize=7,frameon=False)
    fig.suptitle(L(language,'VoxDose 2.0  /  Comparação de gravações','VoxDose 2.0  /  Recording comparison'),x=.02,ha='left',fontsize=12,fontweight='bold',color='#20354A')
    add_credit(fig,language)
    return fig

def export_summary_table(result,folder,language='pt_BR',summary=None):
    """Publication-readable PNG with every reported dose and acoustic measure."""
    import textwrap
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    rows=[];summary=result.summary if summary is None else summary
    for key in METRICS:
        if key in summary:
            name,unit,description=metric(key,language)
            rows.append([name,fmt(summary[key],language,5),unit,'\n'.join(textwrap.wrap(description,78))])
    fig=Figure(figsize=(15,max(5,2.0+.43*len(rows))),dpi=160,facecolor='white');FigureCanvasAgg(fig)
    ax=fig.add_axes([.025,.055,.95,.86]);ax.axis('off')
    table=ax.table(cellText=rows,colLabels=[L(language,'Medida','Measure'),L(language,'Valor','Value'),
        L(language,'Unidade','Unit'),L(language,'Método / interpretação','Method / interpretation')],
        colWidths=[.31,.12,.1,.47],cellLoc='left',colLoc='left',bbox=[0,0,1,1])
    table.auto_set_font_size(False);table.set_fontsize(8.2)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#DDE7EE');cell.set_linewidth(.4);cell.PAD=.035
        if row==0:cell.set_facecolor('#0B3548');cell.set_text_props(color='white',weight='bold',size=9.5)
        else:
            cell.set_facecolor('#F1F7FA' if row%2 else 'white')
            cell.set_text_props(color='#20354A',weight='bold' if col==1 else 'normal')
    fig.text(.025,.974,L(language,'VoxDose 2.0 · Doses vocais e medidas acústicas','VoxDose 2.0 · Vocal doses and acoustic measures'),
        ha='left',va='top',fontsize=17,fontweight='bold',color='#0B3548')
    fig.text(.025,.943,result.label+'  |  '+level_unit(result),ha='left',va='top',fontsize=10,color='#51697B')
    fig.text(.025,.035,L(language,'Traço: medida indisponível. Dd e De são estimativas biomecânicas.','Dash: unavailable measure. Dd and De are biomechanical estimates.'),
        fontsize=8,color='#51697B')
    fig.text(.025,.018,L(language,'Códigos originais de dosimetria: Pasquale Bottalico. Adaptação e desenvolvimento VoxDose: ',
        'Original dosimetry code: Pasquale Bottalico. VoxDose adaptation and development: ')+AUTHOR+' · UFMG',fontsize=8,color='#51697B')
    path=Path(folder)/'VoxDose_results.png';fig.savefig(path,dpi=180,facecolor='white');fig.clear();return path

def export_figures(result,folder,language='pt_BR',separate=True,cancel=None):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    kinds=[None]+KINDS if separate else [None]
    for kind in kinds:
        if cancel is not None and cancel.is_set():
            from .core import Cancelled
            raise Cancelled()
        fig=dashboard(result,language,kind);FigureCanvasAgg(fig)
        name='overview' if kind is None else kind
        fig.savefig(folder/(name+'.png'),dpi=180,facecolor='white')
        fig.savefig(folder/(name+'.svg'),facecolor='white')
        fig.clear()
