"""Run the exact same standalone binary three times without Python on PATH."""
from pathlib import Path
import subprocess,os,sys,json,shutil,time,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from voxdose import __version__
root=Path(__file__).resolve().parents[1];binary=root/'dist'/'VoxDose-2.0.exe'
assert binary.is_file()
sha=hashlib.sha256(binary.read_bytes()).hexdigest();out=root/'validation'/('release_'+__version__);out.mkdir(exist_ok=True)
runs=[]
for number in range(1,4):
    folder=out/f'onefile_round_{number}';folder.mkdir(exist_ok=True)
    standalone=folder/'standalone';standalone.mkdir(exist_ok=True)
    target=standalone/'VoxDose-2.0.exe';shutil.copy2(binary,target)
    assert not (standalone/'_internal').exists()
    assert len(list(standalone.glob('*')))==1
    env=os.environ.copy()
    for key in list(env):
        if key.upper().startswith(('PYTHON','CONDA','VIRTUAL_ENV')):env.pop(key,None)
    env['PATH']=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32')
    env['QT_QPA_PLATFORM']='windows'
    env['VOXDOSE_DATA_DIR']=str(folder/'data')
    start=time.perf_counter()
    # Real hover requires a mapped native window. Hiding the first ShowWindow
    # prevents enter events; these UI tests intentionally show their own app.
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=1
    with (folder/'process.log').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen([str(target),'--self-test'],cwd=standalone,env=env,
            startupinfo=startup,stdout=log,stderr=subprocess.STDOUT)
        try:code=proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill();code=-1
    report=folder/'data'/'verification'/'result.json'
    result=json.loads(report.read_text(encoding='utf-8')) if report.exists() else {'ok':False,'error':'No completion record'}
    import xml.etree.ElementTree as ET
    unit_xml=folder/'unit_tests.xml'
    with (folder/'unit_tests.log').open('w',encoding='utf-8') as log:
        unit=subprocess.run([str(root/'.venv'/'Scripts'/'python.exe'),'-m','pytest','-q',
            '--basetemp='+str(folder/'pytest_tmp'),'--junitxml='+str(unit_xml)],cwd=root,
            stdout=log,stderr=subprocess.STDOUT,timeout=180)
    suite=ET.parse(unit_xml).getroot().find('testsuite') if unit_xml.exists() else None
    unit_count=int(suite.attrib['tests']) if suite is not None else 0
    result.update(round=number,exit_code=code,seconds=time.perf_counter()-start,binary_sha256=sha,
        isolated_executable=True,test_path_excludes_installed_python=True,
        source_unit_tests=unit_count,source_unit_tests_passed=unit.returncode==0)
    # This marker ensures the test opens the full curve options form.
    required=['light_single_axis_curve_editor','dark_single_axis_curve_editor','light_plot_options_dialog','dark_plot_options_dialog']
    result['ok']=bool(result.get('ok') and code==0 and unit.returncode==0 and all(result.get('checks',{}).get(k) for k in required))
    (folder/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    runs.append(result)
    print(json.dumps({'round':number,'ok':result['ok'],'checks':len(result.get('checks',{})),
        'seconds':round(result['seconds'],2),'failures':result.get('failures'), 'exception':result.get('exception')},ensure_ascii=False),flush=True)
summary={'version':__version__,'binary_sha256':sha,'rounds':3,'passed_rounds':sum(r['ok'] for r in runs),
    'all_passed':all(r['ok'] for r in runs),'scope':'Same EXE copied alone; restricted PATH without Python; native Windows Qt; analysis, styles, dialogs, every PNG/SVG export, table PNG and Excel.',
    'limitation':'This is not a clean Windows VM: Python is installed on the development machine, but its PATH and environment are removed and the bundled interpreter is checked.',
    'runs':runs}
(out/'three_runs.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'all_passed':summary['all_passed'],'passed_rounds':summary['passed_rounds'],'sha256':sha},indent=2),flush=True)
if not summary['all_passed']:raise SystemExit(1)
