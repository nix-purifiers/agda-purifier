import http.server
import json
from pathlib import Path
import sys

root, selection, port_file = sys.argv[1:]
entry = json.loads(Path(selection).read_text())["nativeOutput"]
html = ('<!doctype html><html><body><script type="module">import A from "./' + entry +
        '";document.body.dataset.answer=String(A.answer(1n));</script></body></html>').encode()

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=root, **kwargs)
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)
        else:
            super().do_GET()

server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
Path(port_file).write_text(str(server.server_port))
server.serve_forever()
