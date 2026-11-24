"""Export a public portfolio without private host snapshots or collectors."""
from pathlib import Path
import argparse
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGES = ('index.html', 'about/index.html', 'contact/index.html',
         'infrastructure/index.html', 'journal/index.html', 'projects/index.html',
         'projects/self-hosted-cicd/index.html', 'projects/aws-high-availability/index.html',
         'projects/serverless-task-api/index.html', 'projects/infrastructure-monitoring/index.html')
ASSETS = ('app.js', 'styles.css', 'favicon.svg', 'social-preview.svg', 'julio-pardo.jpeg', 'projects.json')

def build(base_path='/pardo-cloud-lab'):
    if not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)*', base_path):
        raise ValueError('Base path must be empty or slash-separated path segments')
    subprocess.run([sys.executable, 'scripts/build.py'], cwd=ROOT, check=True)
    source, output = ROOT / 'website', ROOT / 'pages-site'
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    for name in (*PAGES, *ASSETS):
        src, dest = source / name, output / name
        if src.is_symlink() or not src.is_file():
            raise ValueError(f'Missing or unsafe public asset: {name}')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if name.endswith('.html'):
            html = src.read_text()
            html = re.sub(r'<script src="/telemetry\.js[^"\n]*" defer></script>', '', html)
            html = html.replace('</head>', '<script src="/portfolio.js" defer></script></head>')
            html = html.replace('Connecting to telemetry…', 'Public portfolio · live monitoring stays private')
            html = html.replace('Connecting to the server telemetry collector…', 'Host metrics and query history remain on the private dashboard.')
            html = html.replace('Live host telemetry.', 'Private monitoring architecture.')
            html = html.replace('This private lab does not collect or store contact messages.', 'This portfolio does not collect or store contact messages.')
            html = re.sub(r'(?P<attr>(?:href|src|content)=)(?P<q>["\x27])/(?P<path>[^/"\x27][^"\x27]*|)(?P=q)',
                          lambda m: f'{m["attr"]}{m["q"]}{base_path}/{m["path"]}{m["q"]}', html)
            dest.write_text(html)
        else:
            shutil.copyfile(src, dest)
    shutil.copyfile(ROOT / 'assets/portfolio.js', output / 'portfolio.js')
    (output / 'robots.txt').write_text('User-agent: *\nAllow: /\n')
    (output / '.nojekyll').touch()
    print(f'Public portfolio exported to {output.name} at {base_path or "/"}')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-path', default='/pardo-cloud-lab')
    build(parser.parse_args().base_path)
