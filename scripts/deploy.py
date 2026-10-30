"""Prepare or deploy the support app without changing its existing GitHub repository."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile', default='dataexpert_course')
parser.add_argument('--app', default='support-tickets-andarbech')
parser.add_argument('--apply', action='store_true', help='Attach Lakebase, upload source, and deploy. Default: preview only.')
args = parser.parse_args()

# The existing stock-market app must not be replaced by this support exercise.
if args.apply and args.app == 'lakebase-andarbech-app':
    raise SystemExit('Deployment blocked: lakebase-andarbech-app is the stock-market app. Use --app with a separate, explicitly chosen support app instead.')

def cli(*command, json_output=True):
    result = subprocess.run(['databricks', *command, '--profile', args.profile] + (['-o', 'json'] if json_output else []), capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"Databricks command failed ({' '.join(command[:2])}):\n{result.stderr.strip() or result.stdout.strip()}")
    return json.loads(result.stdout) if json_output and result.stdout.strip() else result.stdout

app = cli('apps', 'get', args.app)
branch = 'projects/dataexpertionewdb/branches/production'
database = branch + '/databases/databricks-postgres'
resources = list(app.get('resources', []))
existing = next((item for item in resources if item['name'] == 'postgres'), None)
resource = {'name': 'postgres', 'postgres': {'branch': branch, 'database': database, 'permission': 'CAN_CONNECT_AND_CREATE'}}
if existing and existing != resource:
    raise SystemExit('A different postgres resource is already attached. Review it before deploying.')
if not existing:
    resources.append(resource)
user = cli('current-user', 'me')['userName']
# Use a new workspace directory so unrelated or stale source files are not deployed.
from datetime import datetime, timezone
suffix = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
workspace = f'/Workspace/Users/{user}/support-app-releases/{suffix}'
print(json.dumps({'app': args.app, 'workspace_source': workspace, 'lakebase': resource, 'existing_resources_preserved': [r['name'] for r in app.get('resources', [])], 'current_compute_status': app.get('compute_status'), 'apply': args.apply}, indent=2))
if not args.apply:
    print('Preview only. Run again with --apply to attach the resource and deploy.')
    raise SystemExit(0)

with tempfile.TemporaryDirectory(prefix='support-app-') as directory:
    stage = Path(directory)
    source = stage / 'source'
    source.mkdir()
    for name in ('app.py', 'lakebase.py', 'app.yaml', 'gunicorn.conf.py', 'requirements.txt', 'requirements.lock.txt'):
        shutil.copy2(ROOT / name, source / name)
    for name in ('templates', 'static'):
        shutil.copytree(ROOT / name, source / name)
    update = stage / 'update.json'
    update.write_text(json.dumps({'update_mask': 'resources', 'app': {'resources': resources}}))
    # With --json, the CLI requires update_mask in the body, despite its help text.
    if not existing:
        cli('apps', 'create-update', args.app, '--json', '@' + str(update))
    cli('workspace', 'import-dir', str(source), workspace, '--overwrite', json_output=False)
    if app.get('compute_status', {}).get('state') == 'STOPPED':
        cli('apps', 'start', args.app)
    result = cli('apps', 'deploy', args.app, '--source-code-path', workspace)
    print(json.dumps(result, indent=2))
print('Deployment complete. Open the app and follow TESTING.md.')
