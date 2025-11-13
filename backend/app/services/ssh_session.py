"""
FINAL SSH MODULE – PTY ONLY + HARD PASSWORD MODE (A1)
-----------------------------------------------------
This version enforces:

✓ PTY always (for full terminal UI)
✓ Absolute disable of all key-based auth
✓ Absolute disable of ssh-agent (even inside PTY)
✓ Only PASSWORD authentication
✓ Auto-detect password prompt or silent fail
✓ Auto-send password exactly once
✓ Structured logging
✓ Safe cleanup
"""

from __future__ import annotations
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache

print(">>> SSH MODULE LOADED (A1: PTY + HARD PASSWORD ONLY)", flush=True)

LOG_DIR = Path(__file__).resolve().parents[2] / "logs" / "ssh_sessions"
LOG_DIR.mkdir(parents=True, exist_ok=True)

SSH_SESSION_IDLE_TIMEOUT = 600
SSH_SESSION_CLOSED_RETENTION = 30

SPECIAL_SEND_KEYS = {
    "enter": "\n", "return": "\n", "tab": "\t", "space": " ",
    "backspace": chr(127), "delete": chr(127), "del": chr(127),
    "esc": chr(27), "escape": chr(27),
    "up": "\x1b[A", "down": "\x1b[B", "left": "\x1b[D", "right": "\x1b[C",
    "home": "\x1bOH", "end": "\x1bOF",
    "pageup": "\x1b[5~", "pagedown": "\x1b[6~",
    "pgup": "\x1b[5~", "pgdn": "\x1b[6~",
    "insert": "\x1b[2~",
    "f1": "\x1bOP", "f2": "\x1bOQ", "f3": "\x1bOR", "f4": "\x1bOS",
    "f5": "\x1b[15~", "f6": "\x1b[17~", "f7": "\x1b[18~",
    "f8": "\x1b[19~", "f9": "\x1b[20~", "f10": "\x1b[21~",
    "f11": "\x1b[23~", "f12": "\x1b[24~",
}

SSH_SESSIONS: Dict[str, "SSHSession"] = {}
SSH_SESSION_LOCK = threading.Lock()


def translate_special_key(key: str) -> Optional[str]:
    if not key:
        return None
    k = key.strip().lower()
    if k in SPECIAL_SEND_KEYS:
        return SPECIAL_SEND_KEYS[k]
    if k.startswith("ctrl+") and len(k) == 6:
        char = k[-1].upper()
        return chr(ord(char) - ord("@"))
    return None


SSH_BINARY_ENV_VAR = "SSH_BINARY"


@lru_cache(maxsize=1)
def _resolve_ssh_client() -> str:
    candidate = os.environ.get(SSH_BINARY_ENV_VAR, "ssh").strip()
    p = Path(candidate)
    if p.is_file() and os.access(p, os.X_OK):
        return str(p)
    path = shutil.which(candidate)
    if path:
        return path
    raise FileNotFoundError("SSH client not found")


# -------------------------------------------------------------------
# BUILD SSH COMMAND – A1 MODE: PASSWORD ONLY, PTY ONLY
# -------------------------------------------------------------------
def build_ssh_command(device: Dict[str, str]) -> List[str]:
    ip = device["device_ip"].strip()
    login = device["device_login_name"].strip()
    ssh = _resolve_ssh_client()

    # 🔥 Hard disable: agent, keys, host keys, and multi-method
    cmd = [
        ssh,
        "-tt",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",

        # 🔥 KEY AUTH DISABLED
        "-o", "PubkeyAuthentication=no",
        "-o", "HostbasedAuthentication=no",
        "-o", "IdentitiesOnly=yes",

        # 🔥 AGENT DISABLED
        "-o", "ForwardAgent=no",
        "-o", "AddKeysToAgent=no",
        "-o", "UseKeychain=no",
        "-o", "IdentityAgent=none",

        # 🔥 ONLY PASSWORD AUTH
        "-o", "PasswordAuthentication=yes",
        "-o", "KbdInteractiveAuthentication=no",  # prevent fallback
        "-o", "PreferredAuthentications=password",
        "-o", "AuthenticationMethods=password",

        # 🔥 NO GSSAPI
        "-o", "GSSAPIAuthentication=no",
        "-o", "GSSAPIKeyExchange=no",
    ]

    port = str(device.get("device_port", "")).strip()
    if port:
        cmd.extend(["-p", port])

    # Identity file ignored but supported:
    identity = (device.get("ssh_identity_file") or "").strip()
    if identity and os.path.isfile(identity):
        cmd.extend(["-i", identity])

    cmd.append(f"{login}@{ip}")
    return cmd


# -------------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------------
def create_session_log_path(device: Dict[str, str], ts: dt.datetime) -> Path:
    name = device.get("device_name", "device").strip().replace(" ", "_")
    return LOG_DIR / f"{name}_ssh_{ts.strftime('%Y%m%d-%H%M%S')}.log"


# -------------------------------------------------------------------
# SSH SESSION — PTY ONLY IMPLEMENTATION
# -------------------------------------------------------------------
class SSHSession:
    def __init__(self, device: Dict[str, str]):
        self.device = device
        self.password = (device.get("device_password") or "").strip()
        self.command = build_ssh_command(device)
        self.session_id = uuid.uuid4().hex
        self.started_at = dt.datetime.now()
        self.log_path = create_session_log_path(device, self.started_at)
        self.closed = False
        self.exit_status = None
        self.last_access = time.time()
        self.master_fd = None
        self._pending_output = []
        self._buffer_lock = threading.Lock()
        self._password_sent = False

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        # 🔥 Hard disable agent even inside PTY
        env["SSH_AUTH_SOCK"] = "/dev/null"
        env["SSH_AGENT_PID"] = ""

        # LOG HEADER
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.log_file.write(
            f"SSH COMMAND: {' '.join(shlex.quote(x) for x in self.command)}\n"
            f"Started: {self.started_at}\n{'-'*60}\n"
        )
        self.log_file.flush()

        print(">>> RUN SSH COMMAND:", " ".join(self.command), flush=True)

        # Always PTY (A1)
        self._start_with_pty(env)

    # -------------------------------------------------------------
    # PTY START (A1 HAS NO PIPE FALLBACK)
    # -------------------------------------------------------------
    def _start_with_pty(self, env):
        import pty
        master, slave = pty.openpty()
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=slave, stdout=slave, stderr=slave,
                close_fds=True, env=env, start_new_session=True,
            )
        finally:
            os.close(slave)
        self.master_fd = master
        self._reader_thread = threading.Thread(target=self._pty_reader, daemon=True)
        self._reader_thread.start()

    # -------------------------------------------------------------
    def _pty_reader(self):
        while True:
            try:
                data = os.read(self.master_fd, 4096)
            except OSError:
                break
            if not data:
                break
            self._handle_output(data.decode(errors="replace"))

    # -------------------------------------------------------------
    # PASSWORD HANDLING
    # -------------------------------------------------------------
    def _handle_output(self, text: str):
        print(">>> OUT:", repr(text), flush=True)

        lower = text.lower()

        # Standard password prompt
        if "password:" in lower and not self._password_sent:
            self._send_password()

        # FortiGate silent mode
        if "permission denied" in lower and not self._password_sent:
            print(">>> FORCE SENDING PASSWORD", flush=True)
            self._send_password()

        # Save output
        with self._buffer_lock:
            self._pending_output.append(text)

        self.log_file.write(text)
        self.log_file.flush()

    # -------------------------------------------------------------
    def _send_password(self):
        if not self.password:
            print(">>> NO PASSWORD PROVIDED", flush=True)
            return
        print(">>> SENDING PASSWORD", flush=True)
        self._password_sent = True
        try:
            os.write(self.master_fd, (self.password + "\n").encode())
        except Exception as exc:
            print(">>> ERROR sending password:", exc, flush=True)

    # -------------------------------------------------------------
    def send_input(self, data: str) -> bool:
        if self.closed:
            return False
        try:
            os.write(self.master_fd, data.replace("\n", "\r").encode())
        except:
            self.close()
            return False
        self.last_access = time.time()
        return True

    # -------------------------------------------------------------
    def _consume_output(self) -> str:
        with self._buffer_lock:
            out = "".join(self._pending_output)
            self._pending_output.clear()
            return out

    # -------------------------------------------------------------
    def poll(self):
        out = self._consume_output()
        if self.process.poll() is not None and not self.closed:
            self.exit_status = self.process.returncode
            out += self.close()
        self.last_access = time.time()
        return {"output": out, "closed": self.closed, "exit_status": self.exit_status}

    # -------------------------------------------------------------
    def close(self):
        if self.closed:
            return ""
        self.closed = True

        try:
            self.process.terminate()
            self.process.wait(timeout=2)
        except:
            pass

        leftover = self._consume_output()

        self.log_file.write(
            f"\n[Session closed at {dt.datetime.now()}] Exit={self.process.returncode}\n"
        )
        self.log_file.flush()
        self.log_file.close()

        return leftover


# -------------------------------------------------------------
# SESSION REGISTRY
# -------------------------------------------------------------
def register_ssh_session(s: SSHSession):
    with SSH_SESSION_LOCK:
        SSH_SESSIONS[s.session_id] = s


def get_ssh_session(session_id: str):
    with SSH_SESSION_LOCK:
        return SSH_SESSIONS.get(session_id)


def remove_ssh_session(session_id: str):
    with SSH_SESSION_LOCK:
        return SSH_SESSIONS.pop(session_id, None)


def cleanup_ssh_sessions():
    now = time.time()
    expired = []
    to_close = []

    with SSH_SESSION_LOCK:
        for sid, s in SSH_SESSIONS.items():
            if now - s.last_access > SSH_SESSION_IDLE_TIMEOUT:
                expired.append(sid)
            elif s.closed and now - s.last_access > SSH_SESSION_CLOSED_RETENTION:
                expired.append(sid)

        for sid in expired:
            s = SSH_SESSIONS.pop(sid, None)
            if s:
                to_close.append(s)

    for s in to_close:
        s.close()


# -------------------------------------------------------------
# WebSocket payload parser
# -------------------------------------------------------------
def parse_websocket_payload(msg: str) -> str:
    if not msg:
        return ""
    try:
        p = json.loads(msg)
    except:
        return msg

    if isinstance(p, str):
        return p

    if isinstance(p, dict):
        for k in ("data", "text", "value"):
            if isinstance(p.get(k), str):
                return p[k]
        special = p.get("key") or p.get("special_key") or p.get("special")
        if isinstance(special, str):
            return translate_special_key(special) or ""
        return ""

    if isinstance(p, list):
        out = []
        for item in p:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                sk = item.get("key") or item.get("special") or item.get("special_key")
                if sk:
                    t = translate_special_key(sk)
                    if t:
                        out.append(t)
                tx = item.get("text") or item.get("value") or item.get("data")
                if tx:
                    out.append(tx)
        return "".join(out)

    return ""
