"""Local synthetic portal for demonstrations; no actual employer or network submission."""
from http.server import BaseHTTPRequestHandler, HTTPServer
HTML = b'''<!doctype html><html><head><title>Mock employer application</title></head>
<body><h1>Synthetic employer portal</h1><p>Local test only. No real application.</p>
<form onsubmit="event.preventDefault();document.getElementById('confirmation').textContent='MOCK-LOCAL-001';window.manualSubmitted=true">
<label>Name <input name="name"></label><label>Email <input name="email" type="email"></label>
<label>Phone <input name="phone"></label><label>CV <input type="file" name="cv"></label>
<label>Cover letter <input type="file" name="cover_letter"></label>
<button type="submit">Submit manually (mock)</button></form><p id="confirmation"></p></body></html>'''
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers(); self.wfile.write(HTML)
    def log_message(self, *args): pass
if __name__ == '__main__':
    print('Synthetic portal: http://127.0.0.1:8765')
    HTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
