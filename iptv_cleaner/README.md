# IPTV Playlist Cleaner & Validator

A production-quality, high-performance command-line utility built in Python 3. It parses IPTV playlist files (`.m3u` or `.m3u8`), checks stream connectivity, validates the stream format using `FFprobe`, and generates a clean playlist with only working, low-latency channels.

Designed to process large playlists containing **10,000 to 100,000+ entries** efficiently with minimal memory usage.

---

## Features

1. **Robust M3U/M3U8 Parser**: Gracefully handles custom `#EXTINF` key-value attributes (e.g., `tvg-id`, `tvg-logo`, `group-title`, `catchup`) and channel names with special characters and commas.
2. **True Stream Verification**: Utilizes `FFprobe` to open the media stream and checks that at least one valid audio or video stream exists, instead of relying solely on HTTP status codes.
3. **Startup Latency & Timeout Control**: Measures actual stream startup times and rejects laggy streams (exceeding 500 ms by default). Validation jobs timeout at 5 seconds by default to prevent hanging.
4. **Duplicate Deduplication**: Automatically detects and discards duplicate URLs, duplicate channel names, and duplicate EXTINF headers, keeping only the first valid occurrence.
5. **Resume Support**: Records processed URLs and saves state. If interrupted, the `--resume` option allows picking up right where it left off, avoiding redundant checking of both dead and alive streams.
6. **Live Dashboard Display**: Renders a premium console interface displaying run speed, elapsed time, ETA, current worker targets, and detailed success/failure counters.
7. **Structured Logging**: Outputs log data to `logs/alive.log`, `logs/dead.log`, and `logs/errors.log`.
8. **Summary Reports**: Saves detailed results to JSON and/or CSV files for further analysis.

---

## Requirements

- **Python 3.12+**
- **FFmpeg (specifically `ffprobe`)** installed and available on your system path.

---

## Installation

On Debian/Ubuntu-based systems, install FFmpeg:
```bash
sudo apt update
sudo apt install ffmpeg
```

Set up a virtual environment and install Python dependencies:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## Usage

Run the program as a module from the workspace root:

```bash
# Basic run with default parameters (reads all files in input/, outputs to output/working.m3u)
python3 -m iptv_cleaner.main

# Run with custom input directory and custom output file path
python3 -m iptv_cleaner.main input -o output/working.m3u --workers 50 --timeout 5.0 --max-latency 500

# Resuming an interrupted validation run
python3 -m iptv_cleaner.main --resume

# Generating summary reports
python3 -m iptv_cleaner.main --json-report report.json --csv-report report.csv
```

### CLI Parameters

| Option | Argument | Default | Description |
| :--- | :--- | :--- | :--- |
| `input_file` | Positional | `input` | Path to the playlist file or directory of playlist files |
| `-o`, `--output` | `path` | `output/working.m3u`| Output playlist filename (inherits extension if input is a `.m3u8` file) |
| `-w`, `--workers` | `int` | `50` | Number of concurrent validation threads |
| `-t`, `--timeout` | `float` | `5.0` | Validation timeout (seconds) per channel |
| `-l`, `--max-latency`| `float` | `500.0` | Max startup latency (milliseconds) allowed |
| `-r`, `--resume` | Flag | `False` | Resume validation from the last run |
| `-v`, `--verbose` | Flag | `False` | Enable verbose console outputs |
| `-a`, `--append` | Flag | `False` | Append valid streams to the output file instead of overwriting |
| `--json-report` | `[path]` | `None` | Save a JSON report summary (defaults to `report.json` if flag present) |
| `--csv-report` | `[path]` | `None` | Save a CSV report summary (defaults to `report.csv` if flag present) |
| `--require-both` | Flag | `False` | Require both video and audio streams to pass validation |
| `--no-retry` | Flag | `False` | Disable retrying failed streams once before marking dead |

---

## Log Output

Logs are written to the `logs/` directory:
- `logs/alive.log`: Logs successful validations with channel name, URL, and latency.
- `logs/dead.log`: Logs stream failures with channel name, URL, latency, and detailed failure reason.
- `logs/errors.log`: Logs system-level errors or exceptions (such as subprocess failures or parsing errors).
- `logs/resume.dat`: Stores processed stream URLs for resumption.
