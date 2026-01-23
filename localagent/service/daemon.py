"""
LocalAgent v3.0 - Daemon Management
"""
import os
import sys
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

SERVICE_DIR = Path.home() / ".localagent"
PID_FILE = SERVICE_DIR / "service" / "daemon.pid"
LOG_FILE = SERVICE_DIR / "logs" / "service.log"
DEFAULT_PORT = 9998

def _ensure_dirs():
    (SERVICE_DIR / "service").mkdir(parents=True, exist_ok=True)
    (SERVICE_DIR / "logs").mkdir(parents=True, exist_ok=True)

def get_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return None

def is_running() -> bool:
    return get_pid() is not None

def start(port: int = DEFAULT_PORT, foreground: bool = False) -> bool:
    _ensure_dirs()
    
    if is_running():
        print(f"⚠️  Already running (PID: {get_pid()})")
        return False
    
    if foreground:
        print(f"🚀 Starting LocalAgent on localhost:{port} (foreground)...")
        os.environ["LOCALAGENT_PORT"] = str(port)
        from . import server
        server.run()
        return True
    
    print(f"🚀 Starting LocalAgent on localhost:{port}...")
    
    log_file = open(LOG_FILE, "a")
    process = subprocess.Popen(
        [sys.executable, "-m", "localagent.service.server"],
        env={**os.environ, "LOCALAGENT_PORT": str(port)},
        stdout=log_file,
        stderr=log_file,
        start_new_session=True
    )
    
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(process.pid))
    
    time.sleep(1)
    if is_running():
        print(f"✅ Started (PID: {process.pid})")
        print(f"   http://localhost:{port}")
        return True
    else:
        print("❌ Failed to start")
        return False

def stop() -> bool:
    pid = get_pid()
    if not pid:
        print("⚠️  Not running")
        return False
    
    print(f"🛑 Stopping (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
        PID_FILE.unlink(missing_ok=True)
        print("✅ Stopped")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def restart(port: int = DEFAULT_PORT) -> bool:
    stop()
    time.sleep(0.5)
    return start(port)

def status() -> dict:
    pid = get_pid()
    return {"running": pid is not None, "pid": pid, "log_file": str(LOG_FILE)}

def print_status():
    s = status()
    print()
    if s["running"]:
        print(f"🟢 Running (PID: {s['pid']})")
    else:
        print("🔴 Stopped")
    print(f"   Logs: {s['log_file']}")
    print()

def tail_logs(lines: int = 50, follow: bool = False):
    if not LOG_FILE.exists():
        print("No logs")
        return
    if follow:
        subprocess.run(["tail", "-f", str(LOG_FILE)])
    else:
        subprocess.run(["tail", f"-{lines}", str(LOG_FILE)])
