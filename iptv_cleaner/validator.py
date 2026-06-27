import json
import subprocess
import time
from typing import Tuple

def validate_stream(
    url: str,
    ffprobe_path: str,
    timeout_seconds: float = 5.0,
    require_both: bool = False
) -> Tuple[bool, float, str]:
    """
    Validates a single stream using ffprobe.
    Does not enforce latency thresholds (latency is validated post-averaging).
    
    Returns:
        A tuple of (is_alive, latency_ms, reason)
    """
    # Convert timeout to microseconds for FFprobe protocols (HTTP, TCP, RTSP)
    timeout_us = int(timeout_seconds * 1_000_000)
    
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-timeout", str(timeout_us),
        "-rw_timeout", str(timeout_us),
        "-analyzeduration", "1000000",  # Limit analysis to 1 second
        "-probesize", "1000000",         # Limit probe to 1 MB
        "-show_streams",
        "-of", "json",
        "-i", url
    ]
    
    start_time = time.perf_counter()
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Enforce Python-side timeout as a fallback
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        if proc.returncode != 0:
            err_msg = stderr.strip() if stderr else f"Exit code {proc.returncode}"
            err_msg = err_msg.replace("\n", " ")[:120]
            return False, latency_ms, f"FFprobe error: {err_msg}"
            
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return False, latency_ms, "Invalid JSON from FFprobe output"
            
        streams = data.get("streams", [])
        if not streams:
            return False, latency_ms, "No media streams identified"
            
        has_video = False
        has_audio = False
        for stream in streams:
            codec_type = stream.get("codec_type")
            if codec_type == "video":
                has_video = True
            elif codec_type == "audio":
                has_audio = True
                
        if require_both:
            if not (has_video and has_audio):
                missing = []
                if not has_video:
                    missing.append("video")
                if not has_audio:
                    missing.append("audio")
                return False, latency_ms, f"Missing streams: {', '.join(missing)}"
        else:
            if not (has_video or has_audio):
                return False, latency_ms, "No playable audio or video stream found"
                
        return True, latency_ms, "ALIVE"
        
    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            proc.wait()
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return False, latency_ms, f"Timeout after {timeout_seconds}s"
    except Exception as e:
        if proc:
            proc.kill()
            proc.wait()
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return False, latency_ms, f"Subprocess exception: {str(e)}"

def validate_stream_average(
    url: str,
    ffprobe_path: str,
    timeout_seconds: float = 5.0,
    max_latency_ms: float = 500.0,
    require_both: bool = False,
    ping_count: int = 5
) -> Tuple[bool, float, str]:
    """
    Executes validate_stream up to ping_count times.
    If the first probe fails, we immediately return False.
    Otherwise, we run the remaining probes and compute the average latency.
    """
    latencies = []
    reasons = []
    
    # 1. First probe
    is_alive, latency_ms, reason = validate_stream(
        url, ffprobe_path, timeout_seconds, require_both
    )
    if not is_alive:
        return False, latency_ms, reason
        
    latencies.append(latency_ms)
    
    # 2. Subsequent probes (only if ping_count > 1)
    for _ in range(1, ping_count):
        probe_alive, probe_latency, probe_reason = validate_stream(
            url, ffprobe_path, timeout_seconds, require_both
        )
        if probe_alive:
            latencies.append(probe_latency)
        else:
            reasons.append(probe_reason)
            
    # Calculate average latency of successful probes
    if not latencies:
        return False, 0.0, f"All probes failed: {'; '.join(set(reasons))}"
        
    avg_latency = sum(latencies) / len(latencies)
    
    if avg_latency > max_latency_ms:
        return False, avg_latency, f"High Latency ({avg_latency:.1f}ms average > {max_latency_ms}ms)"
        
    return True, avg_latency, "ALIVE"

def validate_channel(
    url: str,
    ffprobe_path: str,
    timeout_seconds: float = 5.0,
    max_latency_ms: float = 500.0,
    require_both: bool = False,
    retry: bool = True,
    ping_count: int = 5
) -> Tuple[bool, float, str]:
    """
    Validates a stream URL, retrying once on failure if configured.
    Pings the stream ping_count times and computes average latency.
    """
    is_alive, latency_ms, reason = validate_stream_average(
        url, ffprobe_path, timeout_seconds, max_latency_ms, require_both, ping_count
    )
    
    if not is_alive and retry:
        # Retry once on failure
        is_alive, latency_ms, reason = validate_stream_average(
            url, ffprobe_path, timeout_seconds, max_latency_ms, require_both, ping_count
        )
        
    return is_alive, latency_ms, reason
