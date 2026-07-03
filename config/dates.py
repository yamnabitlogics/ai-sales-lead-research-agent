"""Consistent report timestamps for a single pipeline run."""

from datetime import datetime


class ReportTimestamp:
    """Single source of truth for all dates in one research run."""

    def __init__(self, dt: datetime | None = None):
        self.dt = dt or datetime.now()

    @property
    def iso(self) -> str:
        return self.dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def iso_date(self) -> str:
        return self.dt.strftime("%Y-%m-%d")

    @property
    def display_long(self) -> str:
        return self.dt.strftime("%B %d, %Y")

    @property
    def display_short(self) -> str:
        return self.dt.strftime("%b %d, %Y at %I:%M %p")

    @property
    def filename_stamp(self) -> str:
        return self.dt.strftime("%Y%m%d_%H%M%S")

    @property
    def footer(self) -> str:
        return self.dt.strftime("%B %d, %Y  |  %I:%M %p")
