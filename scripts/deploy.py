"""Unprivileged atomic releases with verified automatic rollback."""
import argparse
import fcntl
import json
from pathlib import Path
import re
import shutil
import time
import urllib.request
from verify import verify
def swap_link(link, target):
    temporary = link.with_name(link.name+'.next')
    temporary.unlink(missing_ok=True); temporary.symlink_to(target); temporary.replace(link)
def verify_http(base, revision):
    for path in ('/','/infrastructure/','/projects/','/journal/','/contact/','/app.js','/telemetry.js','/styles.css'):
        with urllib.request.urlopen(base.rstrip('/')+path, timeout=5) as response:
            if response.status != 200 or not response.read(): raise ValueError(f'Failed response: {path}')
    with urllib.request.urlopen(base.rstrip('/')+'/release.json?check='+str(time.time_ns()), timeout=5) as response:
        actual = json.load(response)['revision']
    if actual != revision: raise ValueError(f'Wrong release served: {actual}')
def deploy(source, base, url):
    source, base = Path(source).resolve(), Path(base).resolve()
    if not base.is_dir(): raise ValueError('Release directory must be provisioned first')
    manifest = verify(source); revision = manifest['revision']
    if not re.fullmatch(r'[a-f0-9]{40}', revision): raise ValueError('Release revision must be a Git commit SHA')
    with (base/'.deploy.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        release = base/(revision+'-'+str(time.time_ns())); shutil.copytree(source, release)
        for path in release.rglob('*'): path.chmod(0o755 if path.is_dir() else 0o644)
        release.chmod(0o755)
        current, previous = base/'current', base/'previous'
        old = current.resolve() if current.is_symlink() else None
        swap_link(current, release.name)
        try: verify_http(url, revision)
        except Exception:
            if old:
                swap_link(current, old.name)
                verify_http(url, json.loads((old/'release.json').read_text())['revision'])
                print('Failed release; previous release restored and verified', flush=True)
            else: current.unlink(missing_ok=True)
            raise
        if old: swap_link(previous, old.name)
        protected = {current.resolve(), previous.resolve() if previous.is_symlink() else current.resolve()}
        releases = sorted((p for p in base.iterdir() if p.is_dir() and not p.is_symlink()), key=lambda p:p.stat().st_mtime, reverse=True)
        for obsolete in releases[5:]:
            if obsolete not in protected and obsolete.parent == base and re.fullmatch(r'[a-f0-9]{40}-[0-9]+', obsolete.name): shutil.rmtree(obsolete)
        print(f'Deployed and verified {revision}', flush=True)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--source',default='website'); parser.add_argument('--base',default='/srv/pardo-cloud-lab/releases'); parser.add_argument('--url',default='http://127.0.0.1:8080')
    args = parser.parse_args(); deploy(args.source,args.base,args.url)
