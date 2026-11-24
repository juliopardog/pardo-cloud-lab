"""Check the public boundary and project-subdirectory navigation."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import importlib.util
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_pages', ROOT / 'scripts/build_pages.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
    def handle_starttag(self, tag, attrs):
        self.urls.extend(value for key, value in attrs if key in ('src', 'href') and value)

class PagesTests(unittest.TestCase):
    def test_public_export_excludes_runtime_data_and_resolves_links(self):
        # Even accidentally present live files must never enter a public export.
        private = ROOT / 'website/telemetry/public-export-test.json'
        private.parent.mkdir(exist_ok=True)
        private.write_text('{"private": true}')
        try:
            for base in ('/pardo-cloud-lab', ''):
                output = module.build(base)
                self.assertFalse((output / 'telemetry').exists())
                self.assertFalse((output / 'telemetry.js').exists())
                self.assertFalse((output / 'release.json').exists())
                self.assertTrue((output / '.nojekyll').exists())
                expected = {*module.PAGES, *module.ASSETS, 'portfolio.js', 'robots.txt', '.nojekyll'}
                self.assertEqual(expected, {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()})
                for page in output.rglob('*.html'):
                    html = page.read_text()
                    self.assertNotIn('telemetry.js', html)
                    parser = Links(); parser.feed(html)
                    for ref in parser.urls:
                        url = urlsplit(ref)
                        if url.scheme or url.netloc or not url.path:
                            continue
                        self.assertTrue(url.path.startswith(base + '/'), ref)
                        relative = unquote(url.path[len(base):].lstrip('/'))
                        target = output / relative
                        if target.is_dir():
                            target /= 'index.html'
                        self.assertTrue(target.resolve().is_relative_to(output), ref)
                        self.assertTrue(target.is_file(), f'{page}: {ref}')
                self.assertNotIn('fetch(', (output / 'portfolio.js').read_text())
        finally:
            private.unlink()
            try:
                private.parent.rmdir()
            except OSError:
                pass
            subprocess.run([sys.executable, 'scripts/build.py'], cwd=ROOT, check=True)

    def test_unsafe_base_path_rejected(self):
        for base in ('/../private', '//example.com', '/x?y', '/x/../y'):
            with self.assertRaises(ValueError):
                module.build(base)

if __name__ == '__main__':
    unittest.main()
