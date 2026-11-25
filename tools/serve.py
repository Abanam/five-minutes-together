"""Static server for local testing with correct MIME types (localhost is a secure context,
so the service worker works).   python tools/serve.py [port] [directory]"""
import functools
import http.server
import sys
from pathlib import Path

TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2", ".mp3": "audio/mpeg", ".txt": "text/plain; charset=utf-8",
    ".pdf": "application/pdf", "": "application/octet-stream",
}


GZIP = {".html", ".js", ".css", ".json", ".svg", ".webmanifest"}


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = TYPES

    def guess_type(self, path):
        return TYPES.get(Path(str(path)).suffix.lower(), "application/octet-stream")

    def do_GET(self):
        # gzip text files like GitHub Pages does, so local timing tests are realistic
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            path = path / "index.html"
        if path.suffix.lower() in GZIP and path.is_file() and "gzip" in self.headers.get("Accept-Encoding", ""):
            import gzip
            data = gzip.compress(path.read_bytes(), 6)
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *args):  # quiet
        pass


def serve(port: int = 8765, directory: str | None = None):
    directory = directory or str(Path(__file__).resolve().parents[1] / "app")
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=directory))
    return httpd


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    d = sys.argv[2] if len(sys.argv) > 2 else None
    httpd = serve(port, d)
    print(f"Serving {d or 'app/'} on http://127.0.0.1:{port}/", flush=True)
    httpd.serve_forever()
