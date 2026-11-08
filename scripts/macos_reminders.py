"""Install/remove a user LaunchAgent. No administrator access or credentials needed."""
import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def launch_agent(root, data):
    root = Path(root).resolve()
    data = Path(data).expanduser().resolve()
    python = root / "backend/venv/bin/python"
    label = "com.hsecareeragent.followups." + hashlib.sha256(str(root).encode()).hexdigest()[:12]
    return {
        "Label": label,
        "ProgramArguments": [str(python), str(root / "scripts/run_followup_reminders.py")],
        "WorkingDirectory": str(root),
        "EnvironmentVariables": {"HSE_DATA_DIR": str(data)},
        "StartInterval": 900,
        "RunAtLoad": True,
        "LimitLoadToSessionType": "Aqua",
        "StandardOutPath": str(data / "logs/reminders.log"),
        "StandardErrorPath": str(data / "logs/reminders-error.log"),
    }


def configure(action, root=ROOT, home=None):
    if sys.platform != "darwin": raise RuntimeError("This scheduler requires macOS. Use setup_reminder_task.ps1 on Windows.")
    root = Path(root).resolve()
    data = Path(os.environ.get("HSE_DATA_DIR", str(root / "data"))).expanduser().resolve()
    agent = launch_agent(root, data)
    directory = Path(home or Path.home()) / "Library/LaunchAgents"
    path = directory / (agent["Label"] + ".plist")
    domain = f"gui/{os.getuid()}"
    target = domain + "/" + agent["Label"]
    if action == "install" and not Path(agent["ProgramArguments"][0]).is_file():
        raise RuntimeError("Run SETUP_HSE_AGENT.command to create the Mac virtual environment first.")
    # Stop only this project's LaunchAgent before updating/removing it.
    existing = subprocess.run(["/bin/launchctl", "print", target], capture_output=True, text=True, timeout=10)
    if existing.returncode == 0:
        result = subprocess.run(["/bin/launchctl", "bootout", target], capture_output=True, text=True, timeout=10)
        if result.returncode != 0: raise RuntimeError("Could not stop the previous reminder task: " + result.stderr.strip())
    if action == "remove":
        path.unlink(missing_ok=True)
        print("Removed this project's Mac reminder task. Application data is preserved.")
        return
    directory.mkdir(parents=True, exist_ok=True)
    (data / "logs").mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(agent))
    path.chmod(0o600)
    result = subprocess.run(["/bin/launchctl", "bootstrap", domain, str(path)], capture_output=True, text=True, timeout=10)
    if result.returncode != 0: raise RuntimeError("Could not load the reminder task: " + result.stderr.strip())
    print("Mac reminders enabled every 15 minutes while signed in and awake. Quiet hours: 22:00–07:00.")
    print("Allow notifications for the macOS scripting process if prompted. No recruiter is contacted.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "remove"])
    args = parser.parse_args()
    try:
        configure(args.action)
        return 0
    except Exception as exc:
        print(f"Reminder setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
