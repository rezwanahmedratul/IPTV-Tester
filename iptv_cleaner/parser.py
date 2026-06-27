import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

def parse_m3u(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parses an M3U/M3U8 playlist file.
    
    Returns:
        A tuple of (header_line, channel_entries)
        where:
          - header_line: The exact first line (e.g. '#EXTM3U' or '#EXTM3U url-tvg="..."')
          - channel_entries: A list of dicts, each representing a channel.
    """
    channels = []
    current_entry = None
    header_line = "#EXTM3U"
    
    def split_extinf(line: str) -> Tuple[str, str]:
        # Split EXTINF by the first comma not enclosed in quotes
        in_quotes = False
        comma_idx = -1
        for i, char in enumerate(line):
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                comma_idx = i
                break
        if comma_idx != -1:
            return line[:comma_idx], line[comma_idx+1:]
        return line, ""

    # Precompile regex to extract key="value" or key=value attributes
    attr_pattern = re.compile(r'([\w\-:]+)\s*=\s*(?:"([^"]*)"|([^\s,]+))')

    if not file_path.exists():
        raise FileNotFoundError(f"Input playlist file not found: {file_path}")

    # Read using utf-8-sig to automatically handle Byte Order Mark (BOM) if present
    with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        is_first_line = True
        for line_idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            if is_first_line:
                is_first_line = False
                if line.startswith("#EXTM3U"):
                    header_line = line
                    continue
            
            if line.startswith("#EXTINF:"):
                inf_part, name = split_extinf(line)
                
                # Extract duration (first word after #EXTINF:)
                duration_part = inf_part[8:].strip()
                parts = duration_part.split(maxsplit=1)
                if parts:
                    duration = parts[0]
                    attrs_str = parts[1] if len(parts) > 1 else ""
                else:
                    duration = "-1"
                    attrs_str = ""
                
                # Parse attributes
                attributes = {}
                for match in attr_pattern.finditer(attrs_str):
                    key = match.group(1)
                    val = match.group(2) if match.group(2) is not None else match.group(3)
                    attributes[key] = val
                
                current_entry = {
                    "extinf_raw": line,
                    "duration": duration,
                    "attributes": attributes,
                    "name": name.strip(),
                    "line_number": line_idx
                }
            elif line.startswith("#"):
                # Other metadata or comments, skip
                continue
            else:
                # URL line
                if current_entry is not None:
                    current_entry["url"] = line
                    channels.append(current_entry)
                    current_entry = None

    return header_line, channels
