"""Run ON macOS to produce, exercise and package a native .app/.dmg/.pkg.

This is intentionally not a Windows cross-compiler. Each output names its
actual architecture. Python is required only on the build machine.
"""
from pathlib import Path
import os,sys,subprocess,shutil,json,platform,hashlib
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from voxdose import __version__

def main():
    if sys.platform!='darwin':
        raise SystemExit('Native macOS required. No macOS binary was generated on this Windows host.')
    from PIL import Image
    architecture=platform.machine();out=root/'dist'/'macos';out.mkdir(parents=True,exist_ok=True)
    work=root/'build'/'macos';work.mkdir(parents=True,exist_ok=True)
    icon=work/'VoxDose.icns'
    with Image.open(root/'voxdose/assets/icon.png') as image:image.save(icon,format='ICNS')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--onedir','--windowed','--name','VoxDose',
        '--distpath',str(out),'--workpath',str(work/'pyinstaller'),'--specpath',str(work),
        '--osx-bundle-identifier','org.voxdose.VoxDose','--icon',str(icon),
        '--hidden-import','PySide6.QtSvg','--hidden-import','openpyxl',
        '--hidden-import','matplotlib.backends.backend_svg','--hidden-import','matplotlib.backends.backend_pdf',
        '--hidden-import','matplotlib.backends.qt_editor.figureoptions',
        '--exclude-module','PyQt5','--exclude-module','PyQt6','--exclude-module','tkinter',
        '--exclude-module','torch','--exclude-module','tensorflow','--exclude-module','sklearn',
        '--exclude-module','librosa','--exclude-module','numba','--exclude-module','IPython',
        '--exclude-module','pytest','--exclude-module','fitz','--exclude-module','pymupdf','--exclude-module','reportlab']
    for source,target in [(root/'voxdose/assets','voxdose/assets'),(root/'docs','docs')]:
        command+=['--add-data',str(source)+':'+target]
    identity=os.environ.get('APPLE_CODESIGN_IDENTITY')
    if identity:command+=['--codesign-identity',identity]
    command.append(str(root/'main.py'))
    subprocess.run(command,cwd=root,check=True)
    app=out/'VoxDose.app';binary=app/'Contents/MacOS/VoxDose'
    subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
    reports=[]
    for number in range(1,4):
        data=work/f'validation_{number}';env=os.environ.copy();env['VOXDOSE_DATA_DIR']=str(data)
        for key in ['PYTHONPATH','PYTHONHOME','VIRTUAL_ENV']:env.pop(key,None)
        env['PATH']='/usr/bin:/bin:/usr/sbin:/sbin'
        subprocess.run([str(binary),'--self-test'],env=env,check=True,timeout=300)
        report=json.loads((data/'verification/result.json').read_text())
        if not report.get('ok'):raise SystemExit('macOS runtime validation failed')
        reports.append(report)
    staging=work/'dmg_content';staging.mkdir(exist_ok=True)
    shutil.copytree(app,staging/app.name,dirs_exist_ok=True,symlinks=True)
    for name in ['Manual_pt_BR.pdf','Manual_en.pdf','RELEASE_2.0.2.md']:
        shutil.copy2(root/'docs'/name,staging/name)
    shutil.copy2(root/'NOTICE.txt',staging/'NOTICE.txt')
    applications=staging/'Applications'
    if not applications.is_symlink():applications.symlink_to('/Applications',target_is_directory=True)
    dmg=out/f'VoxDose-{__version__}-macOS-{architecture}.dmg'
    pkg=out/f'VoxDose-{__version__}-macOS-{architecture}.pkg'
    subprocess.run(['hdiutil','create','-ov','-format','UDZO','-volname','VoxDose 2.0','-srcfolder',str(staging),str(dmg)],check=True)
    subprocess.run(['pkgbuild','--component',str(app),'--install-location','/Applications',
        '--identifier','org.voxdose.VoxDose','--version',__version__,str(pkg)],check=True)
    manifest={'version':__version__,'platform':'macOS','architecture':architecture,'runtime_rounds':reports,
        'developer_id_signed':bool(identity),'notarized':False,
        'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [dmg,pkg]}}
    (out/'macos_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'app':str(app),'dmg':str(dmg),'pkg':str(pkg),'validated_rounds':3},indent=2))

if __name__=='__main__':main()
