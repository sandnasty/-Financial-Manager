"""Minimal representative Financial Manager service."""

from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    """Expose liveness without external packages or configuration."""

    def do_GET(self) -> None:  # noqa: N802 - callback name is defined by stdlib
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok\n")
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        """Keep the baseline quiet; production logging is added separately."""


def main() -> None:
    """Serve the health endpoint on the container's declared port."""
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
