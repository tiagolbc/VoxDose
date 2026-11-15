"""Publish verified Windows downloads; identify macOS sources honestly."""
from pathlib import Path
import sys,json,hashlib,shutil,zipfile,re
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from voxdose import __version__,AUTHOR,AFFILIATION
version=__version__;evidence=root/'validation'/('release_'+version)
binary=root/'dist/VoxDose-2.0.exe';setup=root/'dist'/f'VoxDose-{version}-Windows-Setup.exe'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
runtime=json.loads((evidence/'three_runs.json').read_text(encoding='utf-8'))
installer=json.loads((evidence/'installer_three_runs.json').read_text(encoding='utf-8'))
assert runtime['all_passed'] and runtime['passed_rounds']==3 and runtime['binary_sha256']==digest(binary)
assert installer['all_passed'] and installer['passed_rounds']==3 and installer['setup_sha256']==digest(setup)
assert all(run['application_sha256']==digest(binary) for run in installer['runs'])
for target in [root/'VoxDose-2.0.exe',root/'dist/VoxDose-2.0/VoxDose.exe']:
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(binary,target);assert digest(target)==digest(binary)
for name in [f'VoxDose-{version}-Windows-Setup.exe','VoxDose-2.0-Windows-Setup.exe']:shutil.copy2(setup,root/name)
for folder in [root,root/'dist/VoxDose-2.0']:
    prefs=folder/'settings.ini'
    if prefs.exists():
        prefs.write_text(re.sub(r'(?m)^language=.*$', 'language=en_US',prefs.read_text(encoding='utf-8-sig')),encoding='utf-8')
    if folder!=root:
        for name in ['README.md','NOTICE.txt','CITATION.cff']:shutil.copy2(root/name,folder/name)
legacy=root/'dist/VoxDose-2.0/docs';legacy.mkdir(exist_ok=True)
for path in (root/'docs').iterdir():
    if path.is_file():shutil.copy2(path,legacy/path.name)
manifest={'version':version,'date':'2026-11-15','original_dosimetry_code':'Pasquale Bottalico',
    'voxdose_adaptation_development':AUTHOR,'affiliation':AFFILIATION,'default_language':'en_US',
    'help':'immediate hover or keyboard focus; no modal dialog','exe_sha256':digest(binary),
    'setup_sha256':digest(setup),'windows_signed':False,
    'windows':{'runtime_rounds':3,'source_tests_per_round':[r['source_unit_tests'] for r in runtime['runs']],
        'runtime_checks_per_round':[len(r['checks']) for r in runtime['runs']],
        'installer_rounds':3,'installer_checks_per_round':[len(r['checks']) for r in installer['runs']],
        'installer_compiler':'NSIS 3.13','per_user':True,'python_embedded':True},
    'macos':{'status':'source_only_native_build_pending','binary_created':False,'binary_tested':False,
        'source_package':f'VoxDose-{version}-macOS-build-source.zip',
        'reason':'Windows host; no macOS environment available.'}}
(root/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(root/'release_manifest.json',root/'dist/VoxDose-2.0/release_manifest.json')
portable=root/'VoxDose-2.0-Windows-portable.zip'
with zipfile.ZipFile(portable,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.write(binary,'VoxDose-2.0.exe')
    for name in ['README.md','NOTICE.txt','CITATION.cff','release_manifest.json']:z.write(root/name,name)
    for name in ['Manual_en.pdf','Manual_pt_BR.pdf','Relatorio_VoxDose_2.0.pdf','RELEASE_2.0.2.md']:z.write(root/'docs'/name,'docs/'+name)
    for name in ['three_runs.json','installer_three_runs.json']:z.write(evidence/name,'validation/'+name)
source=root/f'VoxDose-{version}-macOS-build-source.zip'
paths=[root/name for name in ['main.py','pyproject.toml','requirements.txt','README.md','NOTICE.txt','CITATION.cff','Build-macOS.command']]
paths+=list((root/'voxdose').rglob('*.py'))+[p for p in (root/'voxdose/assets').rglob('*') if p.is_file()]
paths+=[root/'tools/build_macos.py']+[root/'docs'/name for name in ['Manual_en.pdf','Manual_pt_BR.pdf','Relatorio_VoxDose_2.0.pdf','RELEASE_2.0.2.md','METHODS.md']]
paths+=[p for p in (root/'examples').iterdir() if p.is_file()]
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in paths:
        arc=path.relative_to(root).as_posix()
        if path.name=='Build-macOS.command':
            info=zipfile.ZipInfo(arc);info.create_system=3;info.external_attr=0o100755<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,path.read_bytes())
        else:z.write(path,arc)
for path in [portable,source]:
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
publish=[root/'VoxDose-2.0.exe',root/f'VoxDose-{version}-Windows-Setup.exe',portable,source]
(root/'SHA256SUMS.txt').write_text('\n'.join(digest(path)+'  '+path.name for path in publish)+'\n',encoding='utf-8')
description=f'''# Website downloads - VoxDose {version}

Recommended Windows download: **VoxDose-{version}-Windows-Setup.exe** (NSIS installer, both manuals included).
Optional Windows download: **VoxDose-2.0.exe** (single portable executable), or **VoxDose-2.0-Windows-portable.zip** (portable plus documentation).
Checksums: SHA256SUMS.txt. Original dosimetry code: Pasquale Bottalico; VoxDose adaptation/development: {AUTHOR}, UFMG.

Do not label VoxDose-{version}-macOS-build-source.zip as a Mac app: it contains source and the native builder only. No Mac binary has been generated or tested. Never upload build/onefile/*.pkg as an Apple package.

Windows: three isolated executable rounds, each with {manifest['windows']['source_tests_per_round'][0]} source tests and {manifest['windows']['runtime_checks_per_round'][0]} runtime checks. Three NSIS install/launch/uninstall rounds each passed {manifest['windows']['installer_checks_per_round'][0]} installer checks and all runtime checks. Development Python remains installed on this Windows machine; the tests remove its PATH/environment and verify the bundled interpreter. No clean-VM or code-signature claim is made.
'''
(root/'WEBSITE_DOWNLOADS.md').write_text(description,encoding='utf-8')
print(json.dumps({'published':[str(path) for path in publish],'macos_binary_created':False,'manifest':manifest},ensure_ascii=False,indent=2))
