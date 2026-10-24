import functools
import hashlib
import http.server
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import deploy
from verify import verify

class ReleaseTests(unittest.TestCase):
    def make_release(self, path, revision):
        path.mkdir()
        names = ['index.html','infrastructure/index.html','projects/index.html','journal/index.html','about/index.html','contact/index.html','app.js','telemetry.js','styles.css']
        for name in names:
            file = path/name; file.parent.mkdir(exist_ok=True, parents=True); file.write_text('release content')
        files = {name:hashlib.sha256((path/name).read_bytes()).hexdigest() for name in names}
        (path/'release.json').write_text(json.dumps({'revision':revision,'files':files}))
    def test_tamper_rejected_before_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.make_release(root/'source','a'*40); (root/'source/app.js').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'Hash mismatch'): verify(root/'source')
    def test_atomic_release_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); base=root/'releases'; base.mkdir()
            self.make_release(root/'first','a'*40); self.make_release(root/'second','b'*40)
            handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(base/'current'))
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
            worker=threading.Thread(target=server.serve_forever,daemon=True); worker.start()
            url=f'http://127.0.0.1:{server.server_port}'
            try:
                deploy.deploy(root/'first',base,url); original=(base/'current').resolve()
                real_check=deploy.verify_http
                def failing_check(base_url,revision):
                    if revision=='b'*40: raise ValueError('simulated failing release')
                    real_check(base_url,revision)
                with patch.object(deploy,'verify_http',side_effect=failing_check):
                    with self.assertRaisesRegex(ValueError,'simulated'): deploy.deploy(root/'second',base,url)
                self.assertEqual((base/'current').resolve(),original)
                real_check(url,'a'*40)
            finally: server.shutdown(); server.server_close()

if __name__=='__main__': unittest.main()
