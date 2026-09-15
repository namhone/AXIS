from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parent
BACKEND = "http://127.0.0.1:8000"


class GatewayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_bytes(self, status, content_type, body, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if headers:
            for key, value in headers:
                if key.lower() in {"content-length", "transfer-encoding", "connection"}:
                    continue
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _proxy_api(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        target = BACKEND + urlsplit(self.path).path
        if urlsplit(self.path).query:
            target += "?" + urlsplit(self.path).query
        headers = {}
        for key in ("Content-Type", "Cookie", "Accept"):
            if self.headers.get(key):
                headers[key] = self.headers[key]
        request = Request(target, data=body, headers=headers, method=self.command)
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read()
                response_headers = list(response.headers.items())
                self._send_bytes(response.status, response.headers.get_content_type(), payload, response_headers)
        except HTTPError as error:
            payload = error.read()
            self._send_bytes(error.code, error.headers.get_content_type(), payload, list(error.headers.items()))
        except URLError as error:
            self._send_bytes(502, "application/json", ('{"error":"backend unavailable: %s"}' % error.reason).encode())

    def _serve_static(self):
        relative = urlsplit(self.path).path.lstrip("/") or "index.html"
        aliases = {
            "dashboard": "pages/dashboard.html",
            "about": "pages/about.html",
            "cv-builder/editor": "pages/cv-builder-editor.html",
        }
        relative = aliases.get(relative, relative)
        file_path = (ROOT / relative).resolve()
        if ROOT not in file_path.parents and file_path != ROOT:
            self._send_bytes(403, "text/plain; charset=utf-8", b"Forbidden")
            return
        if not file_path.is_file():
            self._send_bytes(404, "text/plain; charset=utf-8", b"Not found")
            return
        content_type = "text/html; charset=utf-8"
        suffix = file_path.suffix.lower()
        if suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif suffix == ".js":
            content_type = "text/javascript; charset=utf-8"
        elif suffix == ".json":
            content_type = "application/json"
        elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
            content_type = "image/" + ("svg+xml" if suffix == ".svg" else suffix[1:])
        self._send_bytes(200, content_type, file_path.read_bytes())

    def do_GET(self):
        self._proxy_api() if self.path.startswith("/api/") else self._serve_static()

    def do_POST(self):
        self._proxy_api()

    def do_PUT(self):
        self._proxy_api()

    def do_DELETE(self):
        self._proxy_api()

    def do_OPTIONS(self):
        self._proxy_api() if self.path.startswith("/api/") else self._send_bytes(204, "text/plain", b"")

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8787), GatewayHandler).serve_forever()
