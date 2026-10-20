"""
console_bus.py - Centralized memory ring buffer and real-time log streaming bus.
Intercepts stdout and stderr, captures pipeline stages, and streams events via SSE.
"""

import sys
import os
import io
import time
import json
import asyncio
import threading
from typing import List, Dict, Any, Optional
from collections import deque

MAX_BUFFER_LINES = 5000
LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "app.log")
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)


class ConsoleEntry:
    __slots__ = ("index", "timestamp", "time_str", "level", "message", "source")

    def __init__(self, index: int, level: str, message: str, source: str = "sys"):
        self.index = index
        self.timestamp = time.time()
        self.time_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        self.level = level  # 'INFO', 'STAGE', 'WARN', 'ERROR'
        self.message = message
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "time": self.time_str,
            "level": self.level,
            "message": self.message,
            "source": self.source
        }


class ConsoleBus:
    def __init__(self, maxlen: int = MAX_BUFFER_LINES):
        self.maxlen = maxlen
        self.buffer = deque(maxlen=maxlen)
        self.counter = 0
        self.lock = threading.Lock()
        self.listeners: List[asyncio.Queue] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._log_file = None

        # Keep one previous log; stop app.log from growing without bound.
        try:
            if os.path.getsize(LOG_FILE_PATH) > 2 * 1024 * 1024:
                os.replace(LOG_FILE_PATH, LOG_FILE_PATH + ".old")
        except OSError:
            pass

        try:
            self._log_file = open(LOG_FILE_PATH, "a", encoding="utf-8", buffering=1)
        except Exception:
            pass

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def add_listener(self, queue: asyncio.Queue):
        with self.lock:
            self.listeners.append(queue)

    def remove_listener(self, queue: asyncio.Queue):
        with self.lock:
            if queue in self.listeners:
                self.listeners.remove(queue)

    def publish(self, message: str, level: str = "INFO", source: str = "sys"):
        if not message:
            return

        # Determine level heuristics if not explicitly specified
        msg_upper = message.upper()
        if level == "INFO":
            if any(k in msg_upper for k in ["[ERROR]", "ERROR:", "EXCEPTION", "TRACEBACK", "FAILED"]):
                level = "ERROR"
            elif any(k in msg_upper for k in ["[WARN]", "WARNING:", "DEPRECATION"]):
                level = "WARN"
            elif any(k in msg_upper for k in ["[EXTRACT]", "[WHISPER]", "[RECOVER]", "[UNIFY]", "[CHUNK]", "[CARDS]", "[STAGE]"]):
                level = "STAGE"

        with self.lock:
            self.counter += 1
            entry = ConsoleEntry(self.counter, level, message, source)
            self.buffer.append(entry)

            # Persist to disk log
            if self._log_file:
                try:
                    self._log_file.write(f"[{entry.time_str}] [{entry.level}] {entry.message}\n")
                except Exception:
                    pass

            # Notify active SSE subscribers
            data_dict = entry.to_dict()
            for q in list(self.listeners):
                try:
                    if self._loop and self._loop.is_running():
                        self._loop.call_soon_threadsafe(q.put_nowait, data_dict)
                    else:
                        q.put_nowait(data_dict)
                except Exception:
                    pass

    def get_history(self, limit: int = 1000) -> List[Dict[str, Any]]:
        with self.lock:
            items = list(self.buffer)[-limit:]
            return [e.to_dict() for e in items]

    def clear(self):
        with self.lock:
            self.buffer.clear()
        self.publish("--- Console buffer cleared by user ---", level="INFO")


bus = ConsoleBus()


class StreamInterceptor(io.TextIOBase):
    """Intercepts sys.stdout or sys.stderr, writing to both the original stream and ConsoleBus."""
    def __init__(self, original_stream, default_level: str = "INFO", source_name: str = "stdout"):
        self.original_stream = original_stream
        self.default_level = default_level
        self.source_name = source_name
        self._partial = ""

    def write(self, s: str):
        if not s:
            return 0
        if self.original_stream:
            try:
                self.original_stream.write(s)
                self.original_stream.flush()
            except Exception:
                pass

        lines = s.split("\n")
        if len(lines) == 1:
            self._partial += lines[0]
        else:
            first_line = self._partial + lines[0]
            self._partial = lines[-1]
            if first_line.strip():
                bus.publish(first_line.strip(), level=self.default_level, source=self.source_name)
            for l in lines[1:-1]:
                if l.strip():
                    bus.publish(l.strip(), level=self.default_level, source=self.source_name)
        return len(s)

    def flush(self):
        if self._partial.strip():
            bus.publish(self._partial.strip(), level=self.default_level, source=self.source_name)
            self._partial = ""
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:
                pass


def install_interceptors():
    """Installs stdout and stderr interceptors once at application boot."""
    if not isinstance(sys.stdout, StreamInterceptor):
        sys.stdout = StreamInterceptor(sys.stdout, default_level="INFO", source_name="stdout")
    if not isinstance(sys.stderr, StreamInterceptor):
        sys.stderr = StreamInterceptor(sys.stderr, default_level="WARN", source_name="stderr")


def emit_stage(stage_tag: str, detail: str):
    """Helper function to emit structured pipeline telemetry events."""
    bus.publish(f"[{stage_tag.lower()}] {detail}", level="STAGE", source="pipeline")
