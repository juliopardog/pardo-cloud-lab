"""Restore the previous static release, retaining the current release on failure."""
import json
import fcntl
from pathlib import Path
from deploy import swap_link,verify_http
base=Path('/srv/pardo-cloud-lab/releases')
lock=(base/'.deploy.lock').open('w')
fcntl.flock(lock,fcntl.LOCK_EX)
current,previous=base/'current',base/'previous'
if not current.is_symlink() or not previous.is_symlink(): raise SystemExit('A current and previous release are required')
old,target=current.resolve(),previous.resolve()
if target.parent!=base: raise SystemExit('Previous release is outside the release directory')
swap_link(current,target.name)
try: verify_http('http://127.0.0.1:8080',json.loads((target/'release.json').read_text())['revision'])
except Exception:
    swap_link(current,old.name);raise
swap_link(previous,old.name)
print('Previous release restored and verified')
