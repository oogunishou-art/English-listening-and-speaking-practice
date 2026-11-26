"""テスト用のサーバー（Range 要求に対応。アプリは音声ファイルを Range で分けて読む）。
使い方: python3 dev/test/srv.py <公開するフォルダ> [ポート]"""
import sys, os, re, io
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
ROOT = sys.argv[1]; PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8766

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(self, *a): pass
    def send_head(self):
        rng = self.headers.get('Range'); path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path): return super().send_head()
        m = re.match(r'bytes=(\d*)-(\d*)', rng); size = os.path.getsize(path)
        a = int(m.group(1)) if m.group(1) else size - int(m.group(2)); b = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        b = min(b, size - 1)
        with open(path, 'rb') as f: f.seek(a); data = f.read(b - a + 1)
        self.send_response(206); self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {a}-{b}/{size}'); self.send_header('Content-Length', str(len(data)))
        self.send_header('Accept-Ranges', 'bytes'); self.end_headers()
        return io.BytesIO(data)

ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
