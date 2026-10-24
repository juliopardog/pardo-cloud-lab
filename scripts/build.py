"""Build portable static assets without credentials or runtime state."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import shutil
import subprocess
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
output = ROOT / 'website'
output.mkdir(exist_ok=True)
for asset in (ROOT / 'assets').iterdir():
    if asset.is_file(): shutil.copy2(asset, output / asset.name)
runpy.run_path(str(ROOT / 'generate.py'), run_name='__main__')
(output / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
revision = os.environ.get('GITHUB_SHA') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
files = {str(p.relative_to(output)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'release.json'}
(output / 'release.json').write_text(json.dumps({'revision': revision, 'builtAt': datetime.now(timezone.utc).isoformat(), 'files': files}, indent=2) + '\n')
print(f'Built {len(files)} files for {revision}')
