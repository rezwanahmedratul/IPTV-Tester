import argparse
from pathlib import Path
from typing import NamedTuple, Optional

class Config(NamedTuple):
    input_file: Path
    output_file: Path
    workers: int
    timeout: float
    max_latency: float
    resume: bool
    verbose: bool
    append: bool
    json_report: Optional[Path]
    csv_report: Optional[Path]
    require_both: bool
    retry: bool
    ping_count: int

def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description="High-Performance IPTV Playlist Cleaner & Validator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default="input",
        help="Path to the input M3U/M3U8 playlist file or directory containing files"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path to the output M3U/M3U8 file (defaults to output/working.m3u)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=50,
        help="Number of concurrent validation workers"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=5.0,
        help="Validation timeout in seconds per stream"
    )
    parser.add_argument(
        "-l", "--max-latency",
        type=float,
        default=500.0,
        help="Maximum allowed stream startup latency in milliseconds"
    )
    parser.add_argument(
        "-r", "--resume",
        action="store_true",
        help="Resume validation from the last run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "-a", "--append",
        action="store_true",
        help="Append valid channels to output file instead of overwriting"
    )
    parser.add_argument(
        "--json-report",
        nargs="?",
        const="report.json",
        default=None,
        help="Path to save the JSON summary report"
    )
    parser.add_argument(
        "--csv-report",
        nargs="?",
        const="report.csv",
        default=None,
        help="Path to save the CSV summary report"
    )
    parser.add_argument(
        "--require-both",
        action="store_true",
        help="Require both audio and video streams for validation"
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable retrying failed streams once before marking them dead"
    )
    parser.add_argument(
        "--ping-count",
        type=int,
        default=1,
        help="Number of validation checks per stream to calculate average latency"
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    
    if args.output:
        output_path = Path(args.output)
    else:
        if input_path.is_file() and input_path.suffix == ".m3u8":
            output_path = Path("output/working.m3u8")
        else:
            output_path = Path("output/working.m3u")

    json_report_path = Path(args.json_report) if args.json_report else None
    csv_report_path = Path(args.csv_report) if args.csv_report else None

    return Config(
        input_file=input_path,
        output_file=output_path,
        workers=args.workers,
        timeout=args.timeout,
        max_latency=args.max_latency,
        resume=args.resume,
        verbose=args.verbose,
        append=args.append,
        json_report=json_report_path,
        csv_report=csv_report_path,
        require_both=args.require_both,
        retry=not args.no_retry,
        ping_count=args.ping_count
    )
