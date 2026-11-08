"""Own the local Unix service processes; never stop unrelated services on app ports."""
import argparse
import json
import hmac
import secrets
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def require_free_ports(ports=(8000, 3000)):
    for port in ports:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"Port {port} is already in use. Keep using the running app, or stop its terminal first. No existing service was stopped.") from exc


def wait_until_ready(children, stop, timeout=60):
    deadline = time.monotonic() + timeout
    while not stop.is_set() and time.monotonic() < deadline:
        for name, child in children:
            if child.poll() is not None:
                raise RuntimeError(f"{name} exited before startup completed. Check the service logs.")
        try:
            with urlopen("http://127.0.0.1:8000/health", timeout=1) as response:
                if json.load(response).get("app") != "HSE Career Agent":
                    raise RuntimeError("The service on port 8000 is not HSE Career Agent.")
            with urlopen("http://127.0.0.1:3000", timeout=1):
                return
        except (OSError, ValueError):
            stop.wait(.25)
    raise RuntimeError("Startup was cancelled or timed out. Check the service logs.")


def shutdown_children(children):
    # Each child has its own session; only groups created by this launcher are stopped.
    for _, child in reversed(children):
        if child.poll() is None:
            try: os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError: pass
    for _, child in children:
        try: child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait(timeout=5)


def control_listener(stop):
    """Authenticated loopback shutdown avoids stale PID/process-name assumptions."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(2)
    server.settimeout(.25)
    token = secrets.token_hex(32)
    def listen():
        while not stop.is_set():
            try:
                client, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with client:
                client.settimeout(1)
                try:
                    supplied = client.recv(256).decode("ascii").strip()
                    if hmac.compare_digest(supplied, token):
                        client.sendall(b"stopping\n")
                        stop.set()
                    else:
                        client.sendall(b"denied\n")
                except (OSError, UnicodeError):
                    continue
    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    return server, token, thread


def start(data, no_browser=False):
    import fcntl
    data.mkdir(parents=True, exist_ok=True)
    lock = open(data / "local_app.lock", "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError("The app launcher is already running for this data directory.")
    children, logs = [], []
    state = data / "local_app.json"
    stop = threading.Event()
    handlers = {}
    server = None
    control_thread = None
    try:
        require_free_ports()
        node = shutil.which("node")
        cli = ROOT / "frontend/node_modules/next/dist/bin/next"
        if not node or not cli.is_file():
            raise RuntimeError("Node.js or frontend dependencies are missing. Run SETUP_HSE_AGENT.command.")
        if not (ROOT / "frontend/.next/BUILD_ID").is_file():
            raise RuntimeError("The frontend has not been built. Run SETUP_HSE_AGENT.command, or npm run build in frontend.")
        log_dir = data / "logs"
        log_dir.mkdir(exist_ok=True)
        env = dict(os.environ, HSE_DATA_DIR=str(data), NEXT_TELEMETRY_DISABLED="1")
        commands = [
            ("Backend", [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"], ROOT),
            ("Frontend", [node, str(cli), "start", "-H", "127.0.0.1", "-p", "3000"], ROOT / "frontend")
        ]
        for sig in (signal.SIGINT, signal.SIGTERM):
            handlers[sig] = signal.signal(sig, lambda *_: stop.set())
        for name, command, cwd in commands:
            log = open(log_dir / f"{name.lower()}.log", "a")
            logs.append(log)
            child = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            children.append((name, child))
        server, token, control_thread = control_listener(stop)
        fd = os.open(state, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump({"pid": os.getpid(), "script": str(Path(__file__).resolve()),
                       "control_port": server.getsockname()[1], "token": token}, out)
        print(f"Waiting for services. Logs: {log_dir}", flush=True)
        wait_until_ready(children, stop)
        print("HSE Career Agent ready: http://127.0.0.1:3000", flush=True)
        print("Keep this terminal open. Press Control+C or use STOP_HSE_AGENT.command to stop.", flush=True)
        if not no_browser: webbrowser.open("http://127.0.0.1:3000")
        while not stop.wait(.5):
            for name, child in children:
                if child.poll() is not None:
                    raise RuntimeError(f"{name} exited. Check {log_dir / (name.lower() + '.log')}.")
    finally:
        stop.set()
        if server is not None: server.close()
        if control_thread is not None: control_thread.join(timeout=2)
        shutdown_children(children)
        # A failed second start must not remove another launcher's state.
        if children: state.unlink(missing_ok=True)
        for log in logs: log.close()
        for sig, handler in handlers.items(): signal.signal(sig, handler)
        lock.close()


def stop_app(data):
    state = data / "local_app.json"
    if not state.exists():
        print("No app managed by this launcher is running. Manually started servers must be stopped in their own terminals.")
        return
    try:
        record = json.loads(state.read_text())
        expected = str(Path(__file__).resolve())
        if record.get("script") != expected:
            raise RuntimeError("Saved state does not match this project's launcher. No process was stopped.")
        token = record["token"]
        port = int(record["control_port"])
        if not isinstance(token, str) or len(token) != 64 or not 1 <= port <= 65535:
            raise ValueError("Invalid control state")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
                client.sendall((token + "\n").encode("ascii"))
                if client.recv(256).strip() != b"stopping":
                    raise RuntimeError("Shutdown authentication failed. No process was stopped.")
        except ConnectionRefusedError:
            state.unlink(missing_ok=True)
            print("Removed stale launcher state; no process was stopped.")
            return
        print("Requested shutdown of this project's app services.")
    except (ValueError, KeyError, UnicodeError) as exc:
        raise RuntimeError("Invalid launcher state. No process was stopped.") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop"])
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    data = Path(os.environ.get("HSE_DATA_DIR", str(ROOT / "data"))).expanduser().resolve()
    try:
        if args.action == "start": start(data, args.no_browser)
        else: stop_app(data)
        return 0
    except Exception as exc:
        print(f"Could not {args.action} HSE Career Agent: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
