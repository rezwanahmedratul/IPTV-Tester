import threading
from pathlib import Path
from datetime import datetime
from typing import Set

class IPTVLogger:
    """
    A thread-safe logger that records channel validation outcomes (ALIVE/DEAD/ERROR)
    to respective log files and maintains a state tracking file for resume support.
    """
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.alive_file = self.log_dir / "alive.log"
        self.dead_file = self.log_dir / "dead.log"
        self.errors_file = self.log_dir / "errors.log"
        self.resume_file = self.log_dir / "resume.dat"
        
        self.lock = threading.Lock()

    def log_alive(self, name: str, url: str, latency_ms: float):
        """Logs an active channel to alive.log and updates the resume file."""
        timestamp = datetime.now().isoformat()
        safe_name = name.replace("|", "\\|")
        safe_url = url.replace("|", "\\|")
        log_line = f"{timestamp} | ALIVE | Name: {safe_name} | URL: {safe_url} | Latency: {latency_ms:.1f}ms | Reason: N/A\n"
        with self.lock:
            with open(self.alive_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
            with open(self.resume_file, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")

    def log_dead(self, name: str, url: str, latency_ms: float, reason: str):
        """Logs a dead stream to dead.log and updates the resume file."""
        timestamp = datetime.now().isoformat()
        safe_name = name.replace("|", "\\|")
        safe_url = url.replace("|", "\\|")
        safe_reason = reason.replace("|", "\\|").replace("\n", " ")
        log_line = f"{timestamp} | DEAD | Name: {safe_name} | URL: {safe_url} | Latency: {latency_ms:.1f}ms | Reason: {safe_reason}\n"
        with self.lock:
            with open(self.dead_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
            with open(self.resume_file, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")

    def log_error(self, name: str, url: str, error_msg: str):
        """Logs a process/exception error to errors.log without adding to resume (allows re-trying later)."""
        timestamp = datetime.now().isoformat()
        safe_name = name.replace("|", "\\|")
        safe_url = url.replace("|", "\\|")
        safe_msg = error_msg.replace("|", "\\|").replace("\n", " ")
        log_line = f"{timestamp} | ERROR | Name: {safe_name} | URL: {safe_url} | Message: {safe_msg}\n"
        with self.lock:
            with open(self.errors_file, 'a', encoding='utf-8') as f:
                f.write(log_line)

    def load_processed_urls(self) -> Set[str]:
        """Loads all URLs recorded in the resume file to skip on resumed runs."""
        if not self.resume_file.exists():
            return set()
        with self.lock:
            with open(self.resume_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
