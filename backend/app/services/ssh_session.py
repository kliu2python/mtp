"""
PARAMIKO SSH MODULE – PRECISE AUTHENTICATION CONTROL
-----------------------------------------------------------------------
This version uses Paramiko for complete control over SSH authentication:

✓ Single authentication attempt (no retries)
✓ Keyboard-interactive + password fallback
✓ No SSH agent interference
✓ No multiple key attempts
✓ Full terminal emulation with PTY
✓ Thread-safe output handling
✓ Structured logging
✓ WebSocket compatible
"""

from __future__ import annotations
import datetime as dt
import json
import os
import select
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import paramiko

print(">>> SSH MODULE LOADED (Paramiko-based)", flush=True)

LOG_DIR = Path(__file__).resolve().parents[2] / "logs" / "ssh_sessions"
LOG_DIR.mkdir(parents=True, exist_ok=True)

SSH_SESSION_IDLE_TIMEOUT = 600
SSH_SESSION_CLOSED_RETENTION = 30

SPECIAL_SEND_KEYS = {
    "enter": "\r", "return": "\r", "tab": "\t", "space": " ",
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


def create_session_log_path(device: Dict[str, str], ts: dt.datetime) -> Path:
    name = device.get("device_name", "device").strip().replace(" ", "_")
    return LOG_DIR / f"{name}_ssh_{ts.strftime('%Y%m%d-%H%M%S')}.log"


class InteractiveAuthHandler(paramiko.auth_handler.AuthHandler):
    """
    Custom auth handler that tries keyboard-interactive once, then password once.
    No retries, no multi-key attempts.
    """
    def __init__(self, transport, username, password):
        self.transport = transport
        self.username = username
        self.password = password
        self.authenticated = False
        self.auth_error = None

    def authenticate(self):
        """
        Try authentication methods in order:
        1. keyboard-interactive (common for FortiGate)
        2. password (fallback)
        """
        try:
            # Try keyboard-interactive first
            try:
                self.transport.auth_interactive(
                    self.username,
                    self._interactive_handler
                )
                self.authenticated = True
                return True
            except paramiko.AuthenticationException as e:
                print(f">>> Keyboard-interactive failed: {e}", flush=True)

            # Try password authentication as fallback
            try:
                self.transport.auth_password(self.username, self.password)
                self.authenticated = True
                return True
            except paramiko.AuthenticationException as e:
                print(f">>> Password auth failed: {e}", flush=True)
                self.auth_error = str(e)

            return False

        except Exception as e:
            print(f">>> Authentication error: {e}", flush=True)
            self.auth_error = str(e)
            return False

    def _interactive_handler(self, title, instructions, prompt_list):
        """Handle keyboard-interactive prompts by providing password"""
        print(f">>> Keyboard-interactive: title={title}, prompts={len(prompt_list)}", flush=True)
        if prompt_list:
            # Return password for all prompts
            return [self.password] * len(prompt_list)
        return []


class SSHSession:
    def __init__(self, device: Dict[str, str]):
        self.device = device
        self.password = (device.get("device_password") or "").strip()
        self.username = device["device_login_name"].strip()
        self.hostname = device["device_ip"].strip()
        self.port = int(device.get("device_port", "22"))

        self.session_id = uuid.uuid4().hex
        self.started_at = dt.datetime.now()
        self.log_path = create_session_log_path(device, self.started_at)
        self.closed = False
        self.exit_status = None
        self.last_access = time.time()

        self._pending_output = []
        self._buffer_lock = threading.Lock()
        self._client = None
        self._channel = None
        self._reader_thread = None

        # LOG HEADER
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.log_file.write(
            f"SSH Connection: {self.username}@{self.hostname}:{self.port}\n"
            f"Started: {self.started_at}\n{'-'*60}\n"
        )
        self.log_file.flush()

        # Connect and authenticate
        self._connect()

    def _connect(self):
        """Establish SSH connection with Paramiko"""
        print(f">>> Connecting to {self.hostname}:{self.port} as {self.username}", flush=True)

        # Create SSH client
        self._client = paramiko.SSHClient()

        # Accept all host keys (equivalent to StrictHostKeyChecking=no)
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Configure client to NOT use SSH agent or keys
        self._client._agent = None

        try:
            # Connect (this establishes TCP connection and SSH handshake)
            self._client.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                look_for_keys=False,  # Don't search for SSH keys
                allow_agent=False,    # Don't use SSH agent
                timeout=10,
                auth_timeout=10,
                banner_timeout=10,
                # Try both keyboard-interactive and password
                # Paramiko will try in order and stop after first success
            )

            print(">>> SSH connection established", flush=True)

            # Open interactive shell with PTY
            self._channel = self._client.invoke_shell(
                term='xterm-256color',
                width=120,
                height=40,
                width_pixels=0,
                height_pixels=0
            )

            print(">>> Interactive shell started", flush=True)

            # Start output reader thread
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

        except paramiko.AuthenticationException as e:
            error_msg = f"Authentication failed: {e}\n"
            print(f">>> {error_msg}", flush=True)
            self.log_file.write(error_msg)
            self.log_file.flush()
            self.closed = True
            self.exit_status = 255
            raise

        except Exception as e:
            error_msg = f"Connection failed: {e}\n"
            print(f">>> {error_msg}", flush=True)
            self.log_file.write(error_msg)
            self.log_file.flush()
            self.closed = True
            self.exit_status = 255
            raise

    def _reader_loop(self):
        """Background thread to read SSH output"""
        print(">>> Reader thread started", flush=True)

        try:
            while not self.closed and self._channel:
                # Use select to check if data is available (non-blocking)
                if self._channel.recv_ready():
                    data = self._channel.recv(4096)
                    if data:
                        text = data.decode('utf-8', errors='replace')
                        self._handle_output(text)
                    else:
                        # EOF
                        break
                else:
                    # Small sleep to prevent busy-waiting
                    time.sleep(0.01)

                # Check if channel is still open
                if self._channel.exit_status_ready():
                    # Get any remaining output
                    while self._channel.recv_ready():
                        data = self._channel.recv(4096)
                        if data:
                            text = data.decode('utf-8', errors='replace')
                            self._handle_output(text)
                    break

        except Exception as e:
            print(f">>> Reader error: {e}", flush=True)
        finally:
            print(">>> Reader thread exiting", flush=True)
            if not self.closed:
                self.exit_status = self._channel.recv_exit_status() if self._channel else 1

    def _handle_output(self, text: str):
        """Handle output from SSH session"""
        # Save to buffer
        with self._buffer_lock:
            self._pending_output.append(text)

        # Log to file
        self.log_file.write(text)
        self.log_file.flush()

    def send_input(self, data: str) -> bool:
        """Send input to SSH session"""
        if self.closed or not self._channel:
            return False

        try:
            self._channel.send(data)
            self.last_access = time.time()
            return True
        except Exception as e:
            print(f">>> Send error: {e}", flush=True)
            self.close()
            return False

    def _consume_output(self) -> str:
        """Get and clear pending output"""
        with self._buffer_lock:
            out = "".join(self._pending_output)
            self._pending_output.clear()
            return out

    def poll(self):
        """Poll for output and status"""
        out = self._consume_output()

        # Check if session has ended
        if self._channel and self._channel.exit_status_ready() and not self.closed:
            self.exit_status = self._channel.recv_exit_status()
            out += self.close()

        self.last_access = time.time()
        return {
            "output": out,
            "closed": self.closed,
            "exit_status": self.exit_status
        }

    def close(self):
        """Close SSH session"""
        if self.closed:
            return ""

        self.closed = True
        print(">>> Closing SSH session", flush=True)

        # Get any remaining output
        leftover = self._consume_output()

        # Close channel
        if self._channel:
            try:
                self._channel.close()
            except:
                pass

        # Close client
        if self._client:
            try:
                self._client.close()
            except:
                pass

        # Log closure
        self.log_file.write(
            f"\n[Session closed at {dt.datetime.now()}] Exit={self.exit_status}\n"
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
