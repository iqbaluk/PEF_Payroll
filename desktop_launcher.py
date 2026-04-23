import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from werkzeug.serving import make_server


APP_NAME = "PEF Payroll"
HOST = "127.0.0.1"
PORT = 5001
HEALTH_URL = f"http://{HOST}:{PORT}/healthz"


def _default_data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PEF_Payroll"


def _ensure_runtime_env():
    if not os.environ.get("PEF_PAYROLL_DATA_DIR"):
        os.environ["PEF_PAYROLL_DATA_DIR"] = str(_default_data_dir())


class FlaskServerThread(threading.Thread):
    def __init__(self, flask_app, host: str, port: int):
        super().__init__(name="pef-payroll-server", daemon=True)
        self._server = make_server(host, port, flask_app, threaded=True)

    def run(self):
        self._server.serve_forever()

    def shutdown(self):
        self._server.shutdown()


def _browser_command(url: str, profile_dir: Path):
    profile_dir.mkdir(parents=True, exist_ok=True)
    chrome_paths = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    edge_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]

    for p in chrome_paths + edge_paths:
        if p.exists():
            return [
                str(p),
                f"--app={url}",
                "--new-window",
                "--window-size=1280,900",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={str(profile_dir)}",
            ]
    return None


def _kill_process_tree(pid: int):
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _wait_for_service(timeout_seconds: int = 90) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.5)
    return False


def run(self_test: bool, startup_delay: float, shutdown_delay: float) -> int:
    _ensure_runtime_env()

    from app import app, bootstrap_runtime

    bootstrap_runtime()
    time.sleep(max(0.0, startup_delay))

    try:
        server = FlaskServerThread(app, HOST, PORT)
    except OSError as exc:
        print(f"Failed to bind {HOST}:{PORT}: {exc}")
        return 2

    server.start()

    if not _wait_for_service():
        server.shutdown()
        server.join(timeout=10)
        print("Service failed to become ready in time.")
        return 3

    if self_test:
        time.sleep(1.0)
        server.shutdown()
        server.join(timeout=10)
        time.sleep(max(0.0, shutdown_delay))
        return 0

    runtime_dir = Path(os.environ["PEF_PAYROLL_DATA_DIR"])
    browser_profile_dir = runtime_dir / "browser_profile"
    browser_cmd = _browser_command(f"http://{HOST}:{PORT}", browser_profile_dir)
    if not browser_cmd:
        server.shutdown()
        server.join(timeout=10)
        print("No supported browser found (Edge/Chrome).")
        return 4

    proc = None
    try:
        proc = subprocess.Popen(browser_cmd)
        proc.wait()
    finally:
        if proc and proc.poll() is None:
            _kill_process_tree(proc.pid)

    # Grace period so pending writes complete on slower machines.
    time.sleep(max(0.0, shutdown_delay))
    server.shutdown()
    server.join(timeout=15)
    shutil.rmtree(browser_profile_dir, ignore_errors=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description="PEF Payroll Desktop Launcher")
    parser.add_argument("--self-test", action="store_true", help="Start service and exit after readiness check")
    parser.add_argument("--startup-delay", type=float, default=2.0, help="Delay (seconds) before service startup")
    parser.add_argument("--shutdown-delay", type=float, default=2.0, help="Delay (seconds) before shutdown")
    args = parser.parse_args()

    code = run(args.self_test, args.startup_delay, args.shutdown_delay)
    sys.exit(code)


if __name__ == "__main__":
    main()
