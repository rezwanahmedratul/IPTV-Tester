import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import parse_args, Config
from .utils import find_ffprobe
from .parser import parse_m3u
from .validator import validate_channel
from .writer import PlaylistWriter
from .logger import IPTVLogger
from .progress import ProgressDashboard
from .report import generate_reports

# Global thread synchronization structures
lock = threading.Lock()
processed_urls = set()
written_urls = set()
written_names = set()
written_extinfs = set()
results_list = []

def worker(
    channel: dict,
    config: Config,
    ffprobe_path: str,
    logger: IPTVLogger,
    writer: PlaylistWriter,
    dashboard: ProgressDashboard
) -> dict:
    """
    Worker task that validates a single channel stream.
    """
    url = channel["url"]
    name = channel["name"]
    extinf = channel["extinf_raw"]
    
    # 1. Double check duplicate status before invoking FFprobe (another thread might have validated it)
    with lock:
        if url in written_urls or name in written_names or extinf in written_extinfs:
            return {
                "name": name,
                "url": url,
                "latency_ms": 0.0,
                "status": "SKIPPED",
                "reason": "Duplicate channel name, URL, or EXTINF already written",
                "attributes": channel["attributes"]
            }

    # 2. Execute validation
    is_alive, latency, reason = validate_channel(
        url,
        ffprobe_path,
        timeout_seconds=config.timeout,
        max_latency_ms=config.max_latency,
        require_both=config.require_both,
        retry=config.retry,
        ping_count=config.ping_count
    )
    
    status_str = "ALIVE" if is_alive else "DEAD"
    written = False
    
    if is_alive:
        with lock:
            # Check again under lock before writing to output
            if url not in written_urls and name not in written_names and extinf not in written_extinfs:
                written_urls.add(url)
                written_names.add(name)
                written_extinfs.add(extinf)
                processed_urls.add(url)
                
                writer.write_channel(extinf, url)
                written = True
                
        if written:
            logger.log_alive(name, url, latency)
        else:
            status_str = "SKIPPED"
            reason = "Duplicate entry written by another thread"
    else:
        with lock:
            processed_urls.add(url)
        logger.log_dead(name, url, latency, reason)
        
    dashboard.update(name, latency, status_str, is_alive=(is_alive and written))
    
    return {
        "name": name,
        "url": url,
        "latency_ms": latency,
        "status": status_str,
        "reason": reason,
        "attributes": channel["attributes"]
    }

def main():
    global processed_urls, written_urls, written_names, written_extinfs, results_list
    
    # 1. Parse arguments and configuration
    config = parse_args()
    
    # 2. Locate ffprobe dependency
    try:
        ffprobe_path = find_ffprobe()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 3. Setup Logger and load resume state if requested
    log_dir = Path("logs")
    logger = IPTVLogger(log_dir)
    
    if config.resume:
        # Load previously processed URLs and currently written channels
        processed_urls, written_urls, written_names, written_extinfs = load_resume_state(
            config.output_file, logger
        )
    else:
        processed_urls = set()
        written_urls = set()
        written_names = set()
        written_extinfs = set()
        
    # 4. Parse the input playlist(s)
    all_channels = []
    header_line = "#EXTM3U"
    
    input_path = config.input_file
    m3u_files = []
    if input_path.is_dir():
        # Scan for m3u/m3u8 files, sorted to ensure deterministic order (helps with resume)
        m3u_files = sorted(
            [p for p in input_path.iterdir() if p.is_file() and p.suffix in (".m3u", ".m3u8")]
        )
        if not m3u_files:
            print(f"Error: No .m3u or .m3u8 files found in input directory: {input_path}", file=sys.stderr)
            sys.exit(1)
    else:
        m3u_files = [input_path]
        
    for file_path in m3u_files:
        try:
            f_header, f_channels = parse_m3u(file_path)
            if not all_channels:
                header_line = f_header
            all_channels.extend(f_channels)
        except Exception as e:
            print(f"Error reading playlist {file_path.name}: {e}", file=sys.stderr)
            if len(m3u_files) == 1:
                sys.exit(1)
                
    total_channels = len(all_channels)
    
    # 5. Filter input channels for duplicates and resume compatibility
    submitted_urls = set()
    submitted_extinfs = set()
    channels_to_process = []
    skipped_count = 0
    
    for ch in all_channels:
        url = ch["url"]
        name = ch["name"]
        extinf = ch["extinf_raw"]
        
        # Check against resume state
        if url in processed_urls:
            skipped_count += 1
            continue
            
        # Check against already written files
        if url in written_urls or name in written_names or extinf in written_extinfs:
            skipped_count += 1
            continue
            
        # Pre-deduplicate duplicate URLs or exact EXTINF lines within this run's queue
        if url in submitted_urls or extinf in submitted_extinfs:
            continue
            
        submitted_urls.add(url)
        submitted_extinfs.add(extinf)
        channels_to_process.append(ch)
        
    # 6. Initialize stream writer
    writer = PlaylistWriter(
        config.output_file,
        header_line=header_line,
        append_mode=(config.resume or config.append)
    )
    
    # 7. Start dashboard and executor
    dashboard = ProgressDashboard(total_channels, skipped_count=skipped_count)
    dashboard.start()
    
    start_time = time.perf_counter()
    interrupted = False
    
    try:
        with ThreadPoolExecutor(max_workers=config.workers) as executor:
            futures = {
                executor.submit(
                    worker, ch, config, ffprobe_path, logger, writer, dashboard
                ): ch
                for ch in channels_to_process
            }
            
            for future in as_completed(futures):
                try:
                    res = future.result()
                    with lock:
                        results_list.append(res)
                except Exception as e:
                    ch = futures[future]
                    logger.log_error(ch["name"], ch["url"], f"Thread Exception: {str(e)}")
                    
    except KeyboardInterrupt:
        interrupted = True
        logger.log_error("System", "", "Execution cancelled by user (Ctrl+C)")
        # Cancel all pending tasks in Python 3.9+
        executor.shutdown(wait=False, cancel_futures=True)
    finally:
        dashboard.stop()
        
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    # 8. Compile statistics and write reports
    total_processed = len(results_list)
    alive_count = sum(1 for r in results_list if r["status"] == "ALIVE")
    dead_count = sum(1 for r in results_list if r["status"] == "DEAD")
    skipped_worker = sum(1 for r in results_list if r["status"] == "SKIPPED")
    
    valid_latencies = [r["latency_ms"] for r in results_list if r["status"] == "ALIVE"]
    avg_latency = sum(valid_latencies) / len(valid_latencies) if valid_latencies else 0.0
    
    stats_summary = {
        "timestamp": datetime.now().isoformat(),
        "input_file": str(config.input_file),
        "output_file": str(config.output_file),
        "total_playlist_channels": total_channels,
        "resume_skipped_channels": skipped_count,
        "processed_channels_this_run": total_processed,
        "alive_channels": alive_count,
        "dead_channels": dead_count,
        "skipped_duplicates_in_run": skipped_worker,
        "average_latency_ms": round(avg_latency, 2),
        "elapsed_seconds": round(elapsed, 2),
        "status": "INTERRUPTED" if interrupted else "COMPLETED"
    }
    
    generate_reports(config.json_report, config.csv_report, stats_summary, results_list)
    
    # 9. Print final execution message
    print("\n" + "="*50)
    print(" IPTV Playlist Cleaner & Validator - Execution Summary")
    print("="*50)
    print(f"Status:             {stats_summary['status']}")
    print(f"Total Channels:     {total_channels}")
    print(f"Resume Skipped:     {skipped_count}")
    print(f"Processed:          {total_processed}")
    print(f"  └─ Alive:         {alive_count}")
    print(f"  └─ Dead:          {dead_count}")
    print(f"  └─ Duplicates:    {skipped_worker}")
    print(f"Average Latency:    {stats_summary['average_latency_ms']:.1f} ms")
    print(f"Elapsed Time:       {stats_summary['elapsed_seconds']:.2f} seconds")
    if config.json_report:
        print(f"JSON Report Saved:  {config.json_report}")
    if config.csv_report:
        print(f"CSV Report Saved:   {config.csv_report}")
    print("="*50)

def load_resume_state(output_file: Path, logger: IPTVLogger):
    """
    Helper function to load the state from the resume log and output file.
    """
    processed = logger.load_processed_urls()
    
    written_u = set()
    written_n = set()
    written_e = set()
    
    if output_file.exists() and output_file.stat().st_size > 0:
        try:
            _, channels = parse_m3u(output_file)
            for ch in channels:
                written_u.add(ch["url"])
                written_n.add(ch["name"])
                written_e.add(ch["extinf_raw"])
        except Exception as e:
            logger.log_error("System", str(output_file), f"Resume parsing failed: {str(e)}")
            
    return processed, written_u, written_n, written_e

if __name__ == "__main__":
    main()
