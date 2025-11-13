"""SSH session management utilities using the system ssh client.

This module provides a small wrapper around the OpenSSH client so the
application can maintain interactive SSH sessions via WebSockets while also
recording structured logs on disk.  The implementation is intentionally
threaded and file-based so that it works reliably with Fortinet appliances
where paramiko/asyncssh support may be inconsistent.
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

LOG_DIR = Path(__file__).resolve().parents[2] / "logs" / "ssh_sessions"
LOG_DIR.mkdir(parents=True, exist_ok=True)

SSH_SESSION_IDLE_TIMEOUT = 600  # seconds
SSH_SESSION_CLOSED_RETENTION = 30  # seconds

SPECIAL_SEND_KEYS = {
    "enter": "\n",
    "return": "\n",
    "tab": "\t",
    "space": " ",
    "backspace": chr(127),
    "delete": chr(127),
    "del": chr(127),
    "esc": chr(27),
    "escape": chr(27),
    "up": "\x1b[A",
    "down": "\x1b[B",
    "left": "\x1b[D",
    "right": "\x1b[C",
    "home": "\x1bOH",
    "end": "\x1bOF",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "pgup": "\x1b[5~",
    "pgdn": "\x1b[6~",
    "insert": "\x1b[2~",
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f11": "\x1b[23~",
    "f12": "\x1b[24~",
}

SSH_SESSIONS: Dict[str, "SSHSession"] = {}
SSH_SESSION_LOCK = threading.Lock()


def sanitize_filename_component(value: str) -> str:
    """Return a filesystem friendly representation for log file names."""
    if not value:
        return "device"
    cleaned = [c if c.isalnum() or c in {"-", "_", "."} else "_" for c in value.strip()]
    sanitized = "".join(cleaned).strip("._")
    return sanitized or "device"


def _format_keystrokes(text: str) -> str:
    """Prepare terminal input for logging.

    Currently the terminal logs prefer to store the literal characters that
    were sent to the remote session.  Control characters are therefore written
    as-is so they render naturally when the log is viewed later on.
    """

    return text


def _control_key_value(key: str) -> Optional[str]:
    if not key.lower().startswith("ctrl+"):
        return None
    suffix = key[5:].strip()
    if len(suffix) != 1:
        return None
    char = suffix.upper()
    value = ord(char) - ord("@")
    if 0 < value < 32:
        return chr(value)
    return None


def translate_special_key(key: str) -> Optional[str]:
    """Translate human friendly key names into control sequences."""

    if not key:
        return None
    normalized = key.strip().lower()
    if not normalized:
        return None
    if normalized in SPECIAL_SEND_KEYS:
        return SPECIAL_SEND_KEYS[normalized]
    return _control_key_value(normalized)


SSH_BINARY_ENV_VAR = "SSH_BINARY"


@lru_cache(maxsize=1)
def _resolve_ssh_client() -> str:
    """Return the path to the SSH client executable.

    The backend primarily interacts with the system ``ssh`` binary. Some
    environments used for automated testing do not provide the OpenSSH
    client, so we try to surface a friendly error rather than crashing with
    a ``FileNotFoundError`` when attempting to launch the process.
    ``SSH_BINARY`` can be set to explicitly point at a different executable.
    """

    candidate = os.environ.get(SSH_BINARY_ENV_VAR, "ssh")
    candidate = candidate.strip() or "ssh"

    # Allow callers to provide an absolute or relative path to the
    # executable.  ``shutil.which`` is only used for bare command names.
    potential_path = Path(candidate)
    if potential_path.is_file() and os.access(potential_path, os.X_OK):
        return str(potential_path)

    resolved = shutil.which(candidate)
    if resolved:
        return resolved

    raise FileNotFoundError(
        "SSH client executable not found. Install the OpenSSH client or set "
        "the SSH_BINARY environment variable."
    )


def build_ssh_command(device: Dict[str, str]) -> List[str]:
    ip = device.get("device_ip", "").strip()
    login = device.get("device_login_name", "").strip()
    if not ip or not login:
        raise ValueError("Device IP and login name are required for SSH")

    ssh_client = _resolve_ssh_client()

    command: List[str] = [
        ssh_client,
        "-tt",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
    ]

    port = str(device.get("device_port", "")).strip()
    if port:
        command.extend(["-p", port])

    identity_file = device.get("ssh_identity_file")
    if identity_file:
        identity_file = identity_file.strip()
        if identity_file:
            command.extend(["-i", identity_file])

    extra_options = device.get("ssh_extra_options")
    if extra_options:
        if isinstance(extra_options, str):
            extra = extra_options.split()
        else:
            extra = list(extra_options)
        command.extend(extra)

    command.append(f"{login}@{ip}")
    return command


def create_session_log_path(device: Dict[str, str], timestamp: dt.datetime, session_type: str = "ssh") -> Path:
    # Create log filename with device name, session type, date and time
    device_name = sanitize_filename_component(device.get("device_name", "device"))
    timestamp_str = timestamp.strftime("%Y%m%d-%H%M%S")
    filename = f"{device_name}_{session_type}_{timestamp_str}.log"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / filename


def run_ssh_command_once(device: Dict[str, str]) -> Dict[str, str]:
    ip = device.get("device_ip", "").strip()
    login = device.get("device_login_name", "").strip()
    if not ip or not login:
        raise ValueError("Device IP and login name are required for SSH")

    timestamp = dt.datetime.now()
    log_path = create_session_log_path(device, timestamp)

    ssh_client = _resolve_ssh_client()

    command = [
        ssh_client,
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{login}@{ip}",
    ]
    command_str = " ".join(shlex.quote(part) for part in command)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        exit_status = completed.returncode
        combined = stdout + stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        exit_status = "timeout"
        combined = stdout + stderr + "\n[Session terminated: SSH command timed out]\n"

    header = (
        f"Command: {command_str}\n"
        f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Exit status: {exit_status}\n"
        f"{'-' * 60}\n"
    )
    log_path.write_text(header + combined, encoding="utf-8")

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_status": exit_status,
        "log_path": str(log_path),
        "combined": combined or "[No output captured]",
    }


class SSHSession:
    def __init__(self, device: Dict[str, str]):
        self.device = device
        self.command = build_ssh_command(device)
        self.session_id = uuid.uuid4().hex
        self.started_at = dt.datetime.now()
        self.log_path = create_session_log_path(device, self.started_at)
        self.closed = False
        self.exit_status: Optional[int] = None
        self.last_access = time.time()
        self._pending_output: List[str] = []
        self._buffer_lock = threading.Lock()
        self._current_log_block: Optional[str] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stdin = None
        self.master_fd: Optional[int] = None
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")

        header = (
            f"Command: {' '.join(shlex.quote(part) for part in self.command)}\n"
            f"Started: {self.started_at.isoformat()}\n"
            f"{'-' * 60}\n"
        )
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.log_file.write(header)
        self.log_file.flush()

        self._using_pty = False
        try:
            try:
                self._start_with_pty(env)
                self._using_pty = True
            except OSError:
                self._start_with_pipe(env)
        except Exception:
            self.log_file.close()
            raise

    def _start_with_pty(self, env: Dict[str, str]) -> None:
        import pty

        master_fd, slave_fd = pty.openpty()
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                start_new_session=True,
                env=env,
            )
        finally:
            os.close(slave_fd)
        self.master_fd = master_fd
        self._reader_thread = threading.Thread(target=self._pty_reader_loop, daemon=True)
        self._reader_thread.start()

    def _start_with_pipe(self, env: Dict[str, str]) -> None:
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            close_fds=True,
            start_new_session=True,
            env=env,
        )
        self._stdin = self.process.stdin
        self._reader_thread = threading.Thread(target=self._pipe_reader_loop, daemon=True)
        self._reader_thread.start()

    def _record_output(self, text: str) -> None:
        if not text:
            return
        with self._buffer_lock:
            self._pending_output.append(text)
        self._ensure_log_block("output")
        self._append_log_fragment(text)

    def _record_input(self, text: str) -> None:
        if not text:
            return
        formatted = _format_keystrokes(text)
        if not formatted:
            return
        self._ensure_log_block("input")
        self._append_log_fragment(formatted)

    def _pipe_reader_loop(self) -> None:
        stream = self.process.stdout
        if stream is None:
            return
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            self._record_output(chunk.decode("utf-8", errors="replace"))

    def _pty_reader_loop(self) -> None:
        if self.master_fd is None:
            return
        while True:
            try:
                data = os.read(self.master_fd, 4096)
            except OSError:
                break
            if not data:
                break
            self._record_output(data.decode("utf-8", errors="replace"))

    def _consume_output(self) -> str:
        with self._buffer_lock:
            if not self._pending_output:
                return ""
            output = "".join(self._pending_output)
            self._pending_output.clear()
            return output

    def poll(self) -> Dict[str, object]:
        output = self._consume_output()
        if self.process.poll() is not None and not self.closed:
            self.exit_status = self.process.returncode
            output += self.close()
        self.last_access = time.time()
        return {
            "output": output,
            "closed": self.closed,
            "exit_status": self.exit_status,
        }

    def send_input(self, data: str) -> bool:
        if self.closed:
            return False
        try:
            if self._using_pty:
                # Convert browser newlines to carriage return for PTY-backed sessions.
                data_to_send = data.replace("\n", "\r")
                self._record_input(data)
            else:
                # Non-PTY (pipes) expect newlines; normalize any stray carriage returns.
                data_to_send = data.replace("\r", "\n")
                self._record_input(data)

            encoded = data_to_send.encode("utf-8")
            if self._using_pty and self.master_fd is not None:
                os.write(self.master_fd, encoded)
            else:
                if self._stdin is None:
                    return False
                self._stdin.write(encoded)
                self._stdin.flush()
        except OSError:
            self.close()
            return False
        self.last_access = time.time()
        return True

    def close(self) -> str:
        if self.closed:
            return ""
        self.closed = True
        if self._stdin is not None:
            try:
                self._stdin.close()
            except OSError:
                pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        if self.exit_status is None:
            self.exit_status = self.process.returncode
        if self._reader_thread is not None and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        leftover = self._consume_output()
        footer = (
            f"\n[Session closed at {dt.datetime.now().isoformat()}] Exit status: {self.exit_status}\n"
        )
        self._record_output(footer)
        self._close_current_block()
        leftover += self._consume_output()
        try:
            self.log_file.flush()
        finally:
            self.log_file.close()
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
        self.last_access = time.time()
        return leftover

    def _append_log_fragment(self, fragment: str) -> None:
        if not fragment:
            return
        try:
            self.log_file.write(fragment)
            self.log_file.flush()
        except Exception as exc:  # pragma: no cover
            print(f"[ssh] warning: failed to write log fragment: {exc}", flush=True)

    def _ensure_log_block(self, block_type: str) -> None:
        if self._current_log_block == block_type:
            return
        if self._current_log_block is not None:
            self._append_log_fragment(self._block_end_tag(self._current_log_block))
        self._append_log_fragment(self._block_start_tag(block_type))
        self._current_log_block = block_type

    def _close_current_block(self) -> None:
        if self._current_log_block is None:
            return
        self._append_log_fragment(self._block_end_tag(self._current_log_block))
        self._current_log_block = None

    @staticmethod
    def _block_start_tag(block_type: str) -> str:
        return "<o>" if block_type == "output" else "<i>"

    @staticmethod
    def _block_end_tag(block_type: str) -> str:
        return "</o>" if block_type == "output" else "</i>"


def register_ssh_session(session: SSHSession) -> None:
    with SSH_SESSION_LOCK:
        SSH_SESSIONS[session.session_id] = session


def get_ssh_session(session_id: str) -> Optional[SSHSession]:
    with SSH_SESSION_LOCK:
        return SSH_SESSIONS.get(session_id)


def remove_ssh_session(session_id: str) -> Optional[SSHSession]:
    with SSH_SESSION_LOCK:
        return SSH_SESSIONS.pop(session_id, None)


def cleanup_ssh_sessions() -> None:
    now = time.time()
    expired_ids: List[str] = []
    sessions_to_close: List[SSHSession] = []
    with SSH_SESSION_LOCK:
        for session_id, session in list(SSH_SESSIONS.items()):
            idle = now - session.last_access > SSH_SESSION_IDLE_TIMEOUT
            closed_expired = session.closed and now - session.last_access > SSH_SESSION_CLOSED_RETENTION
            if idle or closed_expired:
                expired_ids.append(session_id)
        for session_id in expired_ids:
            session = SSH_SESSIONS.pop(session_id, None)
            if session is not None:
                sessions_to_close.append(session)
    for session in sessions_to_close:
        session.close()


def parse_websocket_payload(message: str) -> str:
    """Parse an incoming WebSocket payload into terminal data."""

    if not message:
        return ""
    try:
        payload = json.loads(message)
    except ValueError:
        return message

    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        for text_key in ("data", "text", "value"):
            value = payload.get(text_key)
            if isinstance(value, str):
                return value
        for key_field in ("special_key", "special", "key"):
            value = payload.get(key_field)
            if isinstance(value, str):
                translated = translate_special_key(value)
                if translated is not None:
                    return translated
        return ""

    if isinstance(payload, list):
        parts: List[str] = []
        for item in payload:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                key_value = item.get("special_key") or item.get("special") or item.get("key")
                if isinstance(key_value, str):
                    translated = translate_special_key(key_value)
                    if translated is not None:
                        parts.append(translated)
                text_value = item.get("text") or item.get("data") or item.get("value")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "".join(parts)

    return ""
