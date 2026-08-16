"""Legacy import compatibility for the relocated EDF reader."""

from backend.app.eeg.edf_io import read_uniform_edf

__all__ = ["read_uniform_edf"]
