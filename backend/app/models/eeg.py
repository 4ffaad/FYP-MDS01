"""Compatibility exports for legacy API code."""

from backend.app.database.models.eeg import *

# The old prototype called its future prediction table EEGWindowResult.
EEGWindowResult = Prediction

