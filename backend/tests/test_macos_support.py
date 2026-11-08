"""Portable tests for Mac launch, notification and scheduler safety."""
import json
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import sys
import threading
from unittest.mock import Mock, patch
import pytest
from backend.services import notification_service as notifications
from scripts import manage_local_app as manager
from scripts import macos_reminders


def test_mac_notification_passes_user_content_as_arguments():
    title='Job "quote"; $(touch anything)'
    body='Line 1\nLine 2 \\ "quoted"'
    with patch.object(notifications.sys,'platform','darwin'), patch.object(notifications.subprocess,'run',return_value=Mock(returncode=0)) as run:
        assert notifications.send_desktop_notification(title,body)
    args=run.call_args.args[0]
    assert args[:3]==['/usr/bin/osascript','-l','JavaScript']
    assert args[-3:]==['--',title,body]
    assert title not in args[4] and body not in args[4]
    assert not run.call_args.kwargs.get('shell',False)


def test_windows_notification_dispatch_preserved():
    with patch.object(notifications.sys,'platform','win32'), patch.object(notifications,'send_windows_notification',return_value=True) as send:
        assert notifications.send_desktop_notification('Title','Body')
        send.assert_called_once_with('Title','Body')


def test_mac_notification_failure_remains_retryable():
    with patch.object(notifications.sys,'platform','darwin'), patch.object(notifications.subprocess,'run',side_effect=subprocess.TimeoutExpired('osascript',5)):
        assert notifications.send_desktop_notification('Title','Body') is False


def test_unsupported_notification_platform_returns_false():
    with patch.object(notifications.sys,'platform','linux'), patch.object(notifications.subprocess,'run') as run:
        assert not notifications.send_desktop_notification('Title','Body')
        run.assert_not_called()


def test_launcher_refuses_existing_listener():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));sock.listen(1)
        with pytest.raises(RuntimeError,match='already in use'):
            manager.require_free_ports([sock.getsockname()[1]])


def test_launcher_does_not_report_ready_after_child_failure():
    with pytest.raises(RuntimeError,match='exited before startup'):
        manager.wait_until_ready([('Frontend',Mock(poll=lambda:1))],threading.Event(),timeout=1)


def test_launcher_times_out_without_services():
    with pytest.raises(RuntimeError,match='timed out'):
        manager.wait_until_ready([],threading.Event(),timeout=0)


def test_stop_rejects_state_from_another_project(tmp_path):
    state=tmp_path/'local_app.json'
    state.write_text(json.dumps({'script':'/unrelated/project/manage_local_app.py'}))
    with patch.object(manager.socket,'create_connection') as connect:
        with pytest.raises(RuntimeError,match='does not match'):manager.stop_app(tmp_path)
        connect.assert_not_called()


def test_stop_cleans_stale_state_without_signalling(tmp_path):
    state=tmp_path/'local_app.json'
    state.write_text(json.dumps({'script':str(Path(manager.__file__).resolve()),'control_port':54321,'token':'a'*64}))
    with patch.object(manager.socket,'create_connection',side_effect=ConnectionRefusedError):
        manager.stop_app(tmp_path)
    assert not state.exists()


def test_control_listener_requires_its_own_secret():
    stop=threading.Event()
    server,token,thread=manager.control_listener(stop)
    try:
        with socket.create_connection(server.getsockname(),timeout=2) as client:
            client.sendall(b'wrong-token\n');assert client.recv(256).strip()==b'denied'
        assert not stop.is_set()
        with socket.create_connection(server.getsockname(),timeout=2) as client:
            client.sendall((token+'\n').encode());assert client.recv(256).strip()==b'stopping'
        assert stop.wait(2)
    finally:
        stop.set();server.close();thread.join(timeout=2)


def test_launcher_child_cleanup_targets_owned_process_groups():
    child=Mock(pid=12345);child.poll.return_value=None
    with patch.object(manager.os,'killpg') as kill:
        manager.shutdown_children([('Frontend',child)])
    kill.assert_called_once_with(12345,manager.signal.SIGTERM)


def test_launch_agent_handles_spaces_and_distinct_clones(tmp_path):
    root=tmp_path/'My Projects'/'HSE Agent'
    data=tmp_path/'My Personal Data'
    agent=macos_reminders.launch_agent(root,data)
    decoded=plistlib.loads(plistlib.dumps(agent))
    assert decoded['ProgramArguments']==[str(root/'backend/venv/bin/python'),str(root/'scripts/run_followup_reminders.py')]
    assert decoded['StartInterval']==900
    assert decoded['EnvironmentVariables']['HSE_DATA_DIR']==str(data)
    assert decoded['LimitLoadToSessionType']=='Aqua'
    assert agent['Label']!=macos_reminders.launch_agent(tmp_path/'Other Clone',data)['Label']


def test_launch_agent_install_and_remove_are_user_scoped(tmp_path,monkeypatch):
    root=tmp_path/'Project With Spaces';home=tmp_path/'User Home'
    python=root/'backend/venv/bin/python';python.parent.mkdir(parents=True);python.write_text('synthetic')
    monkeypatch.setenv('HSE_DATA_DIR',str(tmp_path/'Personal Data'))
    monkeypatch.setattr(macos_reminders.sys,'platform','darwin')
    with patch.object(macos_reminders.os,'getuid',return_value=501), patch.object(macos_reminders.subprocess,'run',side_effect=[Mock(returncode=1),Mock(returncode=0)]) as run:
        macos_reminders.configure('install',root,home)
        calls=run.call_args_list
        assert calls[-1].args[0][:3]==['/bin/launchctl','bootstrap','gui/501']
    files=list((home/'Library/LaunchAgents').glob('*.plist'));assert len(files)==1
    with patch.object(macos_reminders.os,'getuid',return_value=501), patch.object(macos_reminders.subprocess,'run',side_effect=[Mock(returncode=0),Mock(returncode=0)]):
        macos_reminders.configure('remove',root,home)
    assert not files[0].exists()
    assert python.exists()


def test_scheduler_rejects_non_mac_platform():
    with patch.object(macos_reminders.sys,'platform','linux'):
        with pytest.raises(RuntimeError,match='requires macOS'):macos_reminders.configure('install')

@pytest.mark.launcher
def test_real_launcher_start_duplicate_protection_and_stop(tmp_path):
    if os.environ.get('HSE_RUN_LAUNCHER_TESTS')!='1':
        pytest.skip('Set HSE_RUN_LAUNCHER_TESTS=1 after building the frontend.')
    try: manager.require_free_ports()
    except RuntimeError: pytest.skip('Stop your app first to run the launcher integration test.')
    root=Path(manager.ROOT)
    env=dict(os.environ,HSE_DATA_DIR=str(tmp_path))
    script=str(Path(manager.__file__).resolve())
    with open(tmp_path/'launcher-test.log','w') as log:
        proc=subprocess.Popen([sys.executable,script,'start','--no-browser'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            from urllib.request import urlopen
            import time
            for _ in range(160):
                if proc.poll() is not None:
                    pytest.fail((tmp_path/'launcher-test.log').read_text())
                if 'HSE Career Agent ready:' in (tmp_path/'launcher-test.log').read_text(): break
                time.sleep(.25)
            else: pytest.fail('Launcher never reported readiness.')
            with urlopen('http://127.0.0.1:8000/health') as r:
                assert json.load(r)['app']=='HSE Career Agent'
            duplicate=subprocess.run([sys.executable,script,'start','--no-browser'],cwd=root,env=env,capture_output=True,text=True,timeout=10)
            assert duplicate.returncode==1 and 'already running' in duplicate.stderr
            stopped=subprocess.run([sys.executable,script,'stop'],cwd=root,env=env,capture_output=True,text=True,timeout=10)
            assert stopped.returncode==0,stopped.stderr
            proc.wait(timeout=20)
            assert proc.returncode==0
            assert not (tmp_path/'local_app.json').exists()
            manager.require_free_ports()
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=20)
                except subprocess.TimeoutExpired: proc.kill();proc.wait(timeout=5)
