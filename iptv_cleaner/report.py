import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

def generate_reports(
    json_path: Optional[Path],
    csv_path: Optional[Path],
    stats: Dict[str, Any],
    results: List[Dict[str, Any]]
):
    """
    Generates JSON and/or CSV reports summarizing the playlist validation run.
    """
    if json_path:
        report_data = {
            "summary": stats,
            "channels": results
        }
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4, ensure_ascii=False)
            
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write standard CSV header
            writer.writerow([
                "Name",
                "URL",
                "Group",
                "Latency (ms)",
                "Status",
                "Failure Reason"
            ])
            for ch in results:
                writer.writerow([
                    ch.get("name", ""),
                    ch.get("url", ""),
                    ch.get("attributes", {}).get("group-title", ""),
                    f"{ch.get('latency_ms', 0.0):.1f}",
                    ch.get("status", "UNKNOWN"),
                    ch.get("reason", "")
                ])
