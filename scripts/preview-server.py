from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote
import os

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BASE_PATH = "/daruma-nagano"
PORT = 8000

class PreviewHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(path.split("?", 1)[0].split("#", 1)[0])
        if path == "/":
            return str(REPO_ROOT / "index.html")
        if path.startswith(BASE_PATH + "/"):
            path = path[len(BASE_PATH):]
        elif path == BASE_PATH:
            path = "/"
        # SimpleHTTPRequestHandler の正規化を使うため、一時的にcwdをrootに合わせる
        old_cwd = Path.cwd()
        try:
            os.chdir(REPO_ROOT)
            return super().translate_path(path)
        finally:
            os.chdir(old_cwd)

    def do_GET(self):
        if self.path == "/" or self.path == BASE_PATH:
            self.send_response(302)
            self.send_header("Location", BASE_PATH + "/ja/")
            self.end_headers()
            return
        return super().do_GET()

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), PreviewHandler)
    print("Preview server running")
    print(f"Open: http://127.0.0.1:{PORT}{BASE_PATH}/ja/")
    print("Stop: Ctrl + C")
    server.serve_forever()
