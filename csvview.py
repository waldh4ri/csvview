#!/usr/bin/env python3
"""csvview.py - open CSV / TSV files in the fast local viewer (csv_viewer.html) from the terminal.

    csvview.py data.csv [more.tsv ...]        one browser tab per file
    csvview.py timeline.csv.gz                .gz and .zst are decompressed on the fly
    csvview.py big.csv --no-browser           just print the URL

How it works: a throw-away web server on 127.0.0.1 (random port, random secret path, Host header checked)
serves the viewer page and streams the file to it; the viewer parses everything in the browser. Nothing is
uploaded or sent anywhere. Stop with Ctrl+C.

Viewer features: millions of rows (virtual scrolling), search across all columns (plain or regex), a filter box and a
value picker (checkbox list) on every column, automatic integer / decimal / timestamp detection (type badge in the
header, click it to override) with numeric / chronological sort and range filters (">=2026-09-28", "10..20"),
sort, column resize, row details panel, export of the filtered view. Timestamps without a timezone are read as UTC.
"""
import argparse
import gzip
import http.server
import os
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIEWER = HERE / "csv_viewer.html"


def open_source(path):
    """(file object, size or None) - transparently decompresses .gz / .zst."""
    ext = path.suffix.lower()
    if ext == ".gz":
        return gzip.open(path, "rb"), None
    if ext in (".zst", ".zstd"):
        try:
            from compression import zstd            # Python 3.14+
            return zstd.open(path, "rb"), None
        except ImportError:
            import zstandard
            return zstandard.ZstdDecompressor().stream_reader(open(path, "rb")), None
    return open(path, "rb"), path.stat().st_size


def make_handler(token, files, port):
    page = VIEWER.read_bytes()
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, ctype, body=b"", length=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            if length is not None:
                self.send_header("Content-Length", str(length))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self):
            if self.headers.get("Host", "") not in allowed_hosts:        # DNS-rebinding guard
                return self._send(403, "text/plain", b"forbidden")
            u = urllib.parse.urlparse(self.path)
            parts = [p for p in u.path.split("/") if p]
            if not parts or parts[0] != token:
                return self._send(404, "text/plain", b"not found")
            if len(parts) == 1:
                return self._send(200, "text/html; charset=utf-8", page, len(page))
            if len(parts) == 3 and parts[1] == "data" and parts[2].isdigit() and int(parts[2]) < len(files):
                try:
                    fh, size = open_source(files[int(parts[2])])
                except Exception as e:
                    return self._send(500, "text/plain", str(e).encode())
                with fh:
                    self._send(200, "text/csv; charset=utf-8", length=size)
                    try:
                        while True:
                            chunk = fh.read(1 << 20)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                return
            self._send(404, "text/plain", b"not found")

    return H


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser(description="Open CSV/TSV files in the local fast viewer.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("files", nargs="+", help="CSV / TSV / TXT files (.gz and .zst accepted)")
    ap.add_argument("--port", type=int, default=0, help="listen port (default: random free port)")
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser, only print the URL(s)")
    args = ap.parse_args()
    if not VIEWER.exists():
        sys.exit(f"viewer page not found next to the script: {VIEWER}")
    files = []
    for f in args.files:
        p = Path(f)
        if not p.is_file():
            sys.exit(f"not a file: {f}")
        files.append(p.resolve())
    token = secrets.token_urlsafe(12)
    srv = Server(("127.0.0.1", args.port), None)
    port = srv.server_address[1]
    srv.RequestHandlerClass = make_handler(token, files, port)
    urls = [f"http://127.0.0.1:{port}/{token}/?src=/{token}/data/{i}&name={urllib.parse.quote(p.name)}" for i, p in enumerate(files)]
    for u, p in zip(urls, files):
        print(f"{p.name}: {u}")
    print("serving on 127.0.0.1 only - Ctrl+C to stop", file=sys.stderr)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if not args.no_browser:
        for u in urls:
            webbrowser.open_new_tab(u)
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        pass
    srv.shutdown()


if __name__ == "__main__":
    main()
