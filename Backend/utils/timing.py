"""Timing utilities for performance measurement.

This module provides utilities for measuring and logging
execution times of different stages in the agent pipeline.
"""

import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TimingCollector:
    """Collects timing data for multiple stages of processing.
    
    Attributes:
        timings: Dictionary mapping stage names to their durations in seconds.
        start_time: When the collector was created.
    """
    
    def __init__(self):
        """Initialize an empty timing collector."""
        self.timings: Dict[str, float] = {}
        self.start_time = time.time()
        self._stage_starts: Dict[str, float] = {}
    
    def start_stage(self, stage_name: str) -> None:
        """Start timing a stage.
        
        Args:
            stage_name: Name of the stage to time.
        """
        self._stage_starts[stage_name] = time.time()
    
    def end_stage(self, stage_name: str) -> float:
        """End timing a stage and record the duration.
        
        Args:
            stage_name: Name of the stage to end timing for.
            
        Returns:
            Duration of the stage in seconds.
        """
        if stage_name not in self._stage_starts:
            logger.warning(f"Stage '{stage_name}' was not started")
            return 0.0
        
        duration = time.time() - self._stage_starts[stage_name]
        self.timings[stage_name] = duration
        del self._stage_starts[stage_name]
        return duration
    
    def skip_stage(self, stage_name: str) -> None:
        """Mark a stage as skipped (not timed).
        
        Args:
            stage_name: Name of the stage that was skipped.
        """
        self.timings[stage_name] = -1  # -1 indicates skipped
    
    @contextmanager
    def time_stage(self, stage_name: str):
        """Context manager for timing a stage.
        
        Args:
            stage_name: Name of the stage to time.
            
        Yields:
            None
        """
        self.start_stage(stage_name)
        try:
            yield
        finally:
            duration = self.end_stage(stage_name)
            logger.info(f"[TIMING] {stage_name}: {duration:.2f}s")
    
    def get_total_time(self) -> float:
        """Get total elapsed time since collector creation.
        
        Returns:
            Total time in seconds.
        """
        return time.time() - self.start_time
    
    def get_summary(self) -> str:
        """Get a formatted summary of all timings.
        
        Returns:
            A formatted string with all timings.
        """
        parts = []
        for stage, duration in self.timings.items():
            if duration < 0:
                parts.append(f"{stage}: SKIPPED")
            else:
                parts.append(f"{stage}: {duration:.1f}s")
        
        total = self.get_total_time()
        return f"[TIMING] {', '.join(parts)} | Total: {total:.1f}s"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert timings to a dictionary for API response.
        
        Returns:
            Dictionary with timing data.
        """
        return {
            "stages": {
                k: {"duration_seconds": v, "skipped": v < 0} 
                for k, v in self.timings.items()
            },
            "total_seconds": self.get_total_time()
        }


# Global timing collector for current request (per-request)
_current_timing: Optional[TimingCollector] = None


def get_timing_collector() -> TimingCollector:
    """Get or create the current timing collector.
    
    Returns:
        The current TimingCollector instance.
    """
    global _current_timing
    if _current_timing is None:
        _current_timing = TimingCollector()
    return _current_timing


def reset_timing_collector() -> None:
    """Reset the global timing collector for a new request."""
    global _current_timing
    _current_timing = TimingCollector()


def clear_timing_collector() -> None:
    """Clear the global timing collector."""
    global _current_timing
    _current_timing = None
