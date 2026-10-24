"""Validate release hashes and local HTML asset/navigation references."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import sys
from urllib.parse import unquote, urlsplit
class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.references = []
    def handle_starttag(self, tag, attrs):
        self.references.extend(v for k,v in attrs if k in ('href','src') and v)
def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root/'release.json').read_text())
    if not manifest.get('files'): raise ValueError('Empty release')
    actual = {str(p.relative_to(root)).replace('\\','/') for p in root.rglob('*') if p.is_file() and p.name != 'release.json'}
    if actual != set(manifest['files']): raise ValueError('Release has unexpected or missing files')
    if any(p.is_symlink() or any(part.startswith('.') for part in p.relative_to(root).parts) for p in root.rglob('*')): raise ValueError('Hidden paths or symlinks are not allowed in releases')
    for name, digest in manifest['files'].items():
        path = (root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file(): raise ValueError(f'Missing or unsafe release file: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest: raise ValueError(f'Hash mismatch: {name}')
    for page in root.rglob('*.html'):
        parser = Links(); parser.feed(page.read_text())
        for reference in parser.references:
            url = urlsplit(reference)
            if url.scheme or url.netloc or not url.path or url.path.startswith('/telemetry/'): continue
            target = root/unquote(url.path.lstrip('/')) if url.path.startswith('/') else page.parent/unquote(url.path)
            if target.is_dir(): target = target/'index.html'
            if not target.resolve().is_relative_to(root) or not target.is_file(): raise ValueError(f'Broken link in {page.name}: {reference}')
    for name in ('index.html','infrastructure/index.html','projects/index.html','journal/index.html','about/index.html','contact/index.html','app.js','telemetry.js','styles.css'):
        if name not in manifest['files']: raise ValueError(f'Required file missing: {name}')
    return manifest
if __name__ == '__main__':
    result = verify(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'website')
    print(f"Verified {len(result['files'])} files for {result['revision']}")
