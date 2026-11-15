"""Build a self-contained single EXE, including Python and dynamic plot backends."""
from pathlib import Path
import subprocess,sys,shutil,json
root=Path(__file__).resolve().parents[1]
cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--noupx','--windowed','--name','VoxDose-2.0',
     '--distpath',str(root/'dist'),
     '--workpath',str(root/'build'/'onefile'),
     '--specpath',str(root/'build'),
     '--icon',str(root/'voxdose'/'assets'/'icon.ico'),
     '--add-data',str(root/'voxdose'/'assets')+';voxdose/assets',
     '--hidden-import','PySide6.QtSvg','--hidden-import','openpyxl',
     '--hidden-import','matplotlib.backends.backend_svg',
     '--hidden-import','matplotlib.backends.backend_pdf',
     '--hidden-import','matplotlib.backends.backend_ps',
     '--hidden-import','matplotlib.backends.backend_agg',
     '--hidden-import','matplotlib.backends.qt_editor.figureoptions',
     '--hidden-import','matplotlib.backends.qt_editor.formlayout',
     '--exclude-module','PyQt5','--exclude-module','PyQt6','--exclude-module','tkinter',
     '--exclude-module','torch','--exclude-module','tensorflow','--exclude-module','sklearn',
     '--exclude-module','librosa','--exclude-module','numba','--exclude-module','IPython',
     '--exclude-module','pytest','--exclude-module','pymupdf','--exclude-module','fitz',
     '--exclude-module','reportlab',str(root/'main.py')]
for p in (root/'docs').iterdir():
    if p.is_file():cmd.extend(['--add-data',str(p)+';docs'])
cmd.extend(['--add-data',str(root/'docs'/'images')+';docs/images'])
for p in (root/'examples').iterdir():
    if p.is_file():cmd.extend(['--add-data',str(p)+';examples'])
(root/'build').mkdir(exist_ok=True)
with (root/'build'/'onefile_build.log').open('w',encoding='utf-8') as log:
    completed=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT)
if completed.returncode:raise SystemExit('Build failed; see build/onefile_build.log')
source=root/'dist'/'VoxDose-2.0.exe'
# Inspect the embedded archive: this is not a launcher depending on system Python.
from PyInstaller.archive.readers import CArchiveReader
reader=CArchiveReader(str(source));entries=list(reader.toc)
assert any(n.lower().endswith('python311.dll') for n in entries)
pyz_name=next(n for n in entries if n.lower().endswith('.pyz'))
modules=reader.open_embedded_archive(pyz_name).toc
assert 'matplotlib.backends.backend_svg' in modules
report={'executable':str(source),'single_file':True,'python311_embedded':True,'backend_svg_embedded':True,
        'size_mb':source.stat().st_size/2**20,'archive_entries':len(entries)}
(root/'build'/'onefile_archive.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
