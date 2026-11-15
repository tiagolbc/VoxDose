"""Compile the per-user NSIS installer; leave all user data outside its footprint."""
from pathlib import Path
import subprocess,sys,shutil,os
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from voxdose import __version__
compiler=os.environ.get('MAKENSIS') or shutil.which('makensis')
if not compiler:
    candidates=sorted((root/'tools'/'vendor').glob('nsis-*/makensis.exe'))
    compiler=str(candidates[-1]) if candidates else None
if not compiler:raise SystemExit('NSIS not found. Set MAKENSIS to its compiler path.')
with (root/'build'/'nsis_build.log').open('w',encoding='utf-8') as log:
    result=subprocess.run([compiler,'/V3','/DROOT='+str(root),'/DVERSION='+__version__,str(root/'installer'/'VoxDose.nsi')],
        cwd=root,stdout=log,stderr=subprocess.STDOUT)
if result.returncode:raise SystemExit('NSIS failed; see build/nsis_build.log')
print(root/'dist'/f'VoxDose-{__version__}-Windows-Setup.exe')
