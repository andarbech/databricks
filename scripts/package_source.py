"""Package source without virtual environments, caches, or credentials."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
output = root / 'dist' / 'support-app-source.zip'
output.parent.mkdir(exist_ok=True)
allowed = ['app.py', 'lakebase.py', 'app.yaml', 'gunicorn.conf.py', 'requirements.txt', 'requirements.lock.txt', 'README.md', 'DEPLOYMENT.md', 'TESTING.md', '.gitignore', 'submission/SUBMISSION.md']
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for name in allowed:
        if (root / name).exists():
            archive.write(root / name, name)
    for directory in ['templates', 'static', 'sql', 'scripts', 'tests']:
        for path in sorted((root / directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                archive.write(path, path.relative_to(root))
print(output)
