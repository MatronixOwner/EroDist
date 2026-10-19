#!/usr/bin/env python3
"""Session-only ISO hosting. Bounded authenticated ingest and resumable downloads."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'build/download-site'
DATA.mkdir(parents=True, exist_ok=True)
NAME = 'erodist-0.9.0-mint1-cinnamon-amd64.iso'
PART = DATA / (NAME + '.upload')
ISO = DATA / NAME
TOKEN = (DATA / 'upload-token').read_text().strip()
SIZE = 3201630208
LOCK = threading.Lock()
STATE = {'ready': False, 'sha256': None}

class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def json(self, status, value):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(raw)

    def do_POST(self):
        self.connection.settimeout(120)
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            self.close_connection = True
            return self.json(403, {'error': 'Forbidden'})
        path = urlsplit(self.path)
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= 8 * 1024**2:
                raise ValueError('Invalid body size')
            with LOCK:
                if STATE['ready']:
                    self.close_connection = True
                    return self.json(409, {'error': 'Already published; upload is closed'})
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError('Incomplete request')
                if path.path == '/api/begin':
                    value = json.loads(body)
                    if value.get('output') != NAME or not re.fullmatch('[a-f0-9]{64}', value.get('sha256', '')):
                        raise ValueError('Invalid manifest')
                    if sum(p['size'] for p in value['parts']) != SIZE:
                        raise ValueError('Unexpected ISO size')
                    STATE['sha256'] = value['sha256']
                    if not PART.exists():
                        PART.touch(mode=0o600)
                    return self.json(200, {'bytes': PART.stat().st_size})
                if path.path == '/api/chunk':
                    if not STATE['sha256']:
                        raise ValueError('Begin first')
                    offset = int(parse_qs(path.query)['offset'][0])
                    current = PART.stat().st_size
                    if offset < current and offset + length <= current:
                        with PART.open('rb') as file:
                            file.seek(offset)
                            if file.read(length) == body:
                                return self.json(200, {'bytes': current})
                    if offset != current or offset + length > SIZE:
                        return self.json(409, {'error': 'Offset mismatch', 'bytes': current})
                    with PART.open('ab') as file:
                        file.write(body)
                    return self.json(200, {'bytes': offset + length})
                if path.path == '/api/finalize':
                    if PART.stat().st_size != SIZE or not STATE['sha256']:
                        raise ValueError('Wrong file size')
                    digest = hashlib.sha256()
                    with PART.open('rb') as file:
                        for block in iter(lambda: file.read(4 * 1024**2), b''):
                            digest.update(block)
                    if digest.hexdigest() != STATE['sha256']:
                        raise ValueError('Checksum mismatch')
                    os.replace(PART, ISO)
                    STATE['ready'] = True
                    return self.json(200, {'ready': True, 'sha256': STATE['sha256']})
                return self.json(404, {'error': 'Not found'})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.close_connection = True
            return self.json(400, {'error': str(exc)})

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/status':
            return self.json(200, {**STATE, 'bytes': SIZE if STATE['ready'] else PART.stat().st_size if PART.exists() else 0})
        if path == '/':
            data = (ROOT / 'site/index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)
            return
        if path != '/download/' + NAME:
            return self.json(404, {'error': 'Not found'})
        if not STATE['ready']:
            return self.json(503, {'error': 'ISO is not ready'})
        start, end = 0, SIZE - 1
        requested = self.headers.get('Range')
        if requested:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
            if not match or not any(match.groups()):
                return self.invalid_range()
            a, b = match.groups()
            if not a:
                start = max(0, SIZE - int(b))
            else:
                start, end = int(a), min(int(b), SIZE - 1) if b else SIZE - 1
            if start >= SIZE or end < start:
                return self.invalid_range()
        self.send_response(206 if requested else 200)
        self.send_header('Content-Type', 'application/x-iso9660-image')
        self.send_header('Content-Disposition', 'attachment; filename="' + NAME + '"')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('ETag', '"' + STATE['sha256'] + '"')
        if requested:
            self.send_header('Content-Range', f'bytes {start}-{end}/{SIZE}')
        self.end_headers()
        if self.command == 'HEAD':
            return
        try:
            with ISO.open('rb') as file:
                file.seek(start)
                left = end - start + 1
                while left:
                    chunk = file.read(min(left, 1024**2))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def invalid_range(self):
        self.send_response(416)
        self.send_header('Content-Range', f'bytes */{SIZE}')
        self.send_header('Content-Length', '0')
        self.end_headers()

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
