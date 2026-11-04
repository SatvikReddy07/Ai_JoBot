"""Run a synthetic-only UI demonstration against an isolated temporary database.
Requires a built frontend, dev dependencies and Playwright Chromium.
Refuses to run if the application's normal local ports are already occupied.
"""
import os
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    if not (root/'frontend/.next/BUILD_ID').exists():
        raise SystemExit('Build the frontend first: cd frontend; npm run build')
    for port in (8000,3000):
        with socket.socket() as check:
            try: check.bind(('127.0.0.1',port))
            except OSError: raise SystemExit(f'Stop your local application first. Port {port} is occupied.')
    with tempfile.TemporaryDirectory(prefix='hse_ui_demo_') as directory:
        env=dict(os.environ,HSE_DATA_DIR=directory,NEXT_TELEMETRY_DISABLED='1')
        env.pop('GEMINI_API_KEY',None)
        with open(Path(directory)/'services.log','w') as log:
            subprocess.run([sys.executable,str(root/'scripts/seed_phase4_demo.py')],cwd=root,env=env,check=True,stdout=log,stderr=log)
            backend=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000'],cwd=root,env=env,stdout=log,stderr=log)
            node=shutil.which('node')
            if not node: raise SystemExit('Node.js is required.')
            frontend=subprocess.Popen([node,str(root/'frontend/node_modules/next/dist/bin/next'),'start','-H','127.0.0.1','-p','3000'],cwd=root/'frontend',env=env,stdout=log,stderr=log)
            try:
                for _ in range(60):
                    try:
                        urlopen('http://127.0.0.1:8000/health',timeout=1).close()
                        urlopen('http://127.0.0.1:3000',timeout=1).close()
                        break
                    except Exception: time.sleep(.5)
                else: raise RuntimeError('Synthetic demo services failed to start.')
                runpy.run_path(str(root/'scripts/phase4_ui_scenario.py'),run_name='__main__')
            finally:
                frontend.terminate();backend.terminate()
                for process in (frontend,backend):
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired: process.kill();process.wait(timeout=5)
