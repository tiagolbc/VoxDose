"""Three isolated, actual install/launch/uninstall cycles of the same NSIS setup.

TESTMODE changes only registry and shortcut names so existing installations are
not overwritten. It exercises the same payload, uninstaller and registration.
"""
from pathlib import Path
import subprocess,sys,os,json,hashlib,time,winreg
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from voxdose import __version__
out=root/'validation'/('release_'+__version__);out.mkdir(parents=True,exist_ok=True)
setup=root/'dist'/f'VoxDose-{__version__}-Windows-Setup.exe'
expected=hashlib.sha256((root/'dist/VoxDose-2.0.exe').read_bytes()).hexdigest()
registry=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\VoxDose2.Validation'
menu=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/VoxDose 2.0 Validation'
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
app_startup=subprocess.STARTUPINFO();app_startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;app_startup.wShowWindow=1

def reg_values():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry) as key:
            return {name:winreg.QueryValueEx(key,name)[0] for name in ['DisplayVersion','InstallLocation','UninstallString','Publisher']}
    except FileNotFoundError:return None

if reg_values() is not None or menu.exists():
    raise SystemExit('Existing validation installer registration found; inspect it before proceeding.')
runs=[]
for number in range(1,4):
    folder=out/f'installer_round_{number}';folder.mkdir(exist_ok=True);install=folder/'application with spaces'
    assert install.resolve().is_relative_to(out.resolve())
    if install.exists():raise SystemExit('Refusing to reuse an installer test directory: '+str(install))
    checks={};data=folder/'data';environment=os.environ.copy()
    environment['VOXDOSE_DATA_DIR']=str(data);environment['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
    for key in list(environment):
        if key.upper().startswith(('PYTHON','CONDA','VIRTUAL_ENV')):environment.pop(key,None)
    environment['QT_QPA_PLATFORM']='windows'
    try:
        # NSIS requires /D= as the unquoted final argument, even with spaces.
        # No shell is involved; this is passed directly to CreateProcess.
        command=subprocess.list2cmdline([str(setup),'/S','/TESTMODE=1'])+' /D='+str(install)
        installed=subprocess.run(command,startupinfo=startup,timeout=180)
        checks['install_exit_zero']=installed.returncode==0
        executable=install/'VoxDose-2.0.exe'
        checks['installed_exe_matches_tested_onefile']=hashlib.sha256(executable.read_bytes()).hexdigest()==expected
        checks['both_manuals_and_report']=all((install/'docs'/name).read_bytes()==(root/'docs'/name).read_bytes()
            for name in ['Manual_en.pdf','Manual_pt_BR.pdf','Relatorio_VoxDose_2.0.pdf'])
        checks['installed_marker_present']=(install/'installed.flag').is_file()
        registered=reg_values()
        checks['registered_version_and_location']=bool(registered and registered['DisplayVersion']==__version__ and Path(registered['InstallLocation'])==install)
        checks['publisher_retains_both_attributions']=bool(registered and 'Bottalico' in registered['Publisher'] and 'Cruz' in registered['Publisher'])
        checks['start_menu_app_and_both_manuals']=all((menu/name).is_file() for name in ['VoxDose 2.0.lnk','Manual - English.lnk','Manual - Portugues.lnk','Uninstall.lnk'])
        with (folder/'application.log').open('w',encoding='utf-8') as log:
            launched=subprocess.run([str(executable),'--self-test'],cwd=install,env=environment,
                startupinfo=app_startup,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        runtime=json.loads((data/'verification/result.json').read_text(encoding='utf-8'))
        checks['installed_application_analysis_help_and_exports']=launched.returncode==0 and runtime.get('ok') is True
        checks['installed_default_english']=runtime.get('checks',{}).get('fresh_install_defaults_to_english') is True
        sentinel=install/'user_file_to_preserve.txt';sentinel.write_text('User-owned file: must survive uninstall.',encoding='utf-8')
        result_file=data/'user_result_to_preserve.txt';result_file.write_text('Retained user analysis.',encoding='utf-8')
    finally:
        uninstaller=install/'Uninstall.exe'
        if uninstaller.exists():
            removed=subprocess.run([str(uninstaller),'/S'],startupinfo=startup,timeout=60)
            deadline=time.monotonic()+30
            while time.monotonic()<deadline and ((install/'VoxDose-2.0.exe').exists() or reg_values()):time.sleep(.1)
            checks['uninstall_exit_zero']=removed.returncode==0
            checks['uninstall_removed_program_and_registration']=not (install/'VoxDose-2.0.exe').exists() and reg_values() is None
            checks['uninstall_removed_shortcuts']=not menu.exists()
            checks['uninstall_preserved_user_files']=(install/'user_file_to_preserve.txt').is_file() and (data/'user_result_to_preserve.txt').is_file()
    report={'round':number,'ok':all(checks.values()),'checks':checks,'runtime':runtime,
        'setup_sha256':hashlib.sha256(setup.read_bytes()).hexdigest(),'application_sha256':expected}
    (folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    runs.append(report);print(json.dumps({'round':number,'ok':report['ok'],'installer_checks':len(checks),'runtime_checks':len(runtime['checks'])}),flush=True)
    if not report['ok']:raise SystemExit('Installer round failed; see '+str(folder))
summary={'version':__version__,'all_passed':all(r['ok'] for r in runs),'passed_rounds':len(runs),
    'setup_sha256':hashlib.sha256(setup.read_bytes()).hexdigest(),'runs':runs}
(out/'installer_three_runs.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'all_installer_rounds_passed':summary['all_passed'],'rounds':len(runs)}),flush=True)
