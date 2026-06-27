import time
import threading
from datetime import timedelta
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.text import Text

class ProgressDashboard:
    """
    A premium CLI dashboard constructed using the rich library.
    It displays real-time statistics, a progress bar, elapsed time, ETA, 
    and the status of the current channel validation.
    """
    def __init__(self, total_channels: int, skipped_count: int = 0):
        self.total = total_channels
        self.skipped = skipped_count
        self.processed = 0  # Number of channels processed in this run
        self.alive = 0
        self.dead = 0
        self.total_latency_sum = 0.0
        
        self.current_channel = "Initializing..."
        self.current_latency = 0.0
        self.current_status = "PENDING"
        
        self.start_time = time.perf_counter()
        self.lock = threading.RLock()
        
        self.console = Console()
        self.live: Optional[Live] = None

    def start(self):
        """Starts the live dashboard refresh loop."""
        self.live = Live(self.get_layout(), console=self.console, refresh_per_second=4, screen=False)
        self.live.start()

    def stop(self):
        """Stops the live dashboard, making a final screen update."""
        if self.live:
            # Final update to show actual complete stats
            self.live.update(self.get_layout())
            self.live.stop()

    def update(self, channel_name: str, latency: float, status: str, is_alive: bool):
        """Thread-safe update of the validation progress metrics."""
        with self.lock:
            self.processed += 1
            if is_alive:
                self.alive += 1
                self.total_latency_sum += latency
            else:
                self.dead += 1
            self.current_channel = channel_name
            self.current_latency = latency
            self.current_status = status
            
            if self.live:
                self.live.update(self.get_layout())

    def get_layout(self) -> Layout:
        """Assembles the dashboard layout panels with formatting and color themes."""
        with self.lock:
            processed_total = self.processed + self.skipped
            remaining = self.total - processed_total
            elapsed = time.perf_counter() - self.start_time
            
            # Speed and ETA calculations
            if self.processed > 0:
                speed = self.processed / elapsed
                eta_sec = remaining / speed
                eta_str = str(timedelta(seconds=int(eta_sec)))
            else:
                speed = 0.0
                eta_str = "Calculating..."
                
            elapsed_str = str(timedelta(seconds=int(elapsed)))
            avg_latency = self.total_latency_sum / self.alive if self.alive > 0 else 0.0
            pct = (processed_total / self.total * 100) if self.total > 0 else 0.0
            
            # Header Row
            header_table = Table.grid(expand=True)
            header_table.add_column(justify="center", ratio=1)
            header_table.add_row(Text("IPTV PLAYLIST CLEANER & VALIDATOR", style="bold cyan"))
            header_table.add_row(Text("High-Performance Stream Verification Utility", style="dim italic"))
            
            # Panel 1: Progress Summary Info
            prog_table = Table.grid(padding=(0, 1))
            prog_table.add_column(style="bold yellow", width=18)
            prog_table.add_column(style="white")
            prog_table.add_row("Total Playlist:", f"{self.total}")
            prog_table.add_row("Skipped/Resume:", f"{self.skipped}")
            prog_table.add_row("Processed (Run):", f"{self.processed}")
            prog_table.add_row("Remaining:", f"{remaining}")
            prog_table.add_row("Elapsed Time:", elapsed_str)
            prog_table.add_row("ETA:", f"[green]{eta_str}[/green]")
            prog_table.add_row("Velocity:", f"{speed:.1f} ch/s")
            
            # Format Progress Bar
            bar_width = 24
            filled = int(pct / 100 * bar_width)
            bar_str = "█" * filled + "░" * (bar_width - filled)
            prog_table.add_row("Completion:", f"[{bar_str}] {pct:.1f}%")
            
            # Panel 2: Current Validator Detail
            cur_table = Table.grid(padding=(0, 1))
            cur_table.add_column(style="bold blue", width=15)
            cur_table.add_column(style="white")
            
            # Truncate channel name to fit standard widths
            display_name = self.current_channel
            if len(display_name) > 28:
                display_name = display_name[:25] + "..."
            
            cur_table.add_row("Channel:", display_name)
            cur_table.add_row("Latency:", f"{self.current_latency:.1f} ms")
            
            status_style = "bold green" if "ALIVE" in self.current_status else "bold red"
            cur_table.add_row("Status:", f"[{status_style}]{self.current_status}[/{status_style}]")
            
            # Panel 3: Stats counters
            stats_table = Table.grid(padding=(0, 1))
            stats_table.add_column(style="bold magenta", width=15)
            stats_table.add_column(style="white")
            stats_table.add_row("Working (Alive):", f"[green]{self.alive}[/green]")
            stats_table.add_row("Dead / Failed:", f"[red]{self.dead}[/red]")
            stats_table.add_row("Avg Latency:", f"{avg_latency:.1f} ms")
            
            # Create Panel wrappers
            header_panel = Panel(header_table, border_style="cyan")
            progress_panel = Panel(prog_table, title="[yellow]Progress[/yellow]", border_style="yellow")
            current_panel = Panel(cur_table, title="[blue]Active Job[/blue]", border_style="blue")
            stats_panel = Panel(stats_table, title="[magenta]Statistics[/magenta]", border_style="magenta")
            
            # Assemble full dashboard layout
            main_layout = Layout()
            main_layout.split_column(
                Layout(header_panel, name="header", size=4),
                Layout(name="body")
            )
            
            body_layout = main_layout["body"]
            body_layout.split_row(
                Layout(progress_panel, name="progress", ratio=4),
                Layout(current_panel, name="current", ratio=4),
                Layout(stats_panel, name="stats", ratio=3)
            )
            
            return main_layout
