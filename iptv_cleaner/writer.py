import threading
from pathlib import Path

class PlaylistWriter:
    """
    A thread-safe writer that appends validated IPTV channels to the output file immediately.
    """
    def __init__(self, file_path: Path, header_line: str = "#EXTM3U", append_mode: bool = False):
        self.file_path = file_path
        self.lock = threading.Lock()
        
        # Write the header line if we are overwriting (append_mode=False),
        # or if the file does not exist, or if the file is empty.
        write_header = not append_mode or not file_path.exists() or file_path.stat().st_size == 0
        
        if not append_mode:
            with self.lock:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(f"{header_line}\n")
        else:
            if write_header:
                with self.lock:
                    self.file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.file_path, "w", encoding="utf-8") as f:
                        f.write(f"{header_line}\n")

    def write_channel(self, extinf_raw: str, url: str):
        """
        Appends a channel's #EXTINF line and stream URL to the output file in a thread-safe manner.
        Flushes the file descriptor immediately to prevent loss of progress.
        """
        with self.lock:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(f"{extinf_raw}\n")
                f.write(f"{url}\n")
                f.flush()
