import shutil
from pathlib import Path

def find_ffprobe() -> str:
    """
    Finds the path to the ffprobe executable on the system path or in common locations.
    Raises FileNotFoundError if ffprobe is not found.
    """
    path = shutil.which("ffprobe")
    if path:
        return path
    
    # Common locations on Unix-like systems
    common_paths = [
        "/usr/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        "/bin/ffprobe",
        "/opt/homebrew/bin/ffprobe" # macOS Homebrew standard
    ]
    
    for p in common_paths:
        if Path(p).exists():
            return p
            
    raise FileNotFoundError(
        "ffprobe executable not found on the system PATH. "
        "Please install FFmpeg (which contains ffprobe) before running this program."
    )
