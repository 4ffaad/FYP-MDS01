import numpy as np
from scipy import signal
from scipy.signal import butter, filtfilt


class EEGPreprocessor:
    """Apply the project's fixed four-step preprocessing pipeline.

    Input and output use ``(channels, samples)`` arrays. No channel changes,
    resampling, windowing, or model-specific reshaping occur in this class.
    """

    def __init__(
        self,
        sampling_rate=256,
        low_freq=0.5,
        high_freq=100,
        notch_freq=60,
    ):
        self.fs = sampling_rate
        self.low_freq = low_freq
        self.high_freq = high_freq
        self.notch_freq = notch_freq

    def bandpass_filter(self, data, order=4):
        """Remove frequencies outside the configured 0.5–100 Hz range."""

        nyquist = self.fs / 2

        if not 0 < self.low_freq < nyquist:
            raise ValueError("Low cutoff must be above 0 Hz and below Nyquist.")
        if self.high_freq <= self.low_freq:
            raise ValueError("High cutoff must be greater than low cutoff.")

        low = self.low_freq / nyquist
        high = min(self.high_freq / nyquist, 0.99)

        b, a = butter(
            order,
            [low, high],
            btype="band",
        )

        if data.ndim == 1:
            return filtfilt(b, a, data)

        return np.array([
            filtfilt(b, a, channel)
            for channel in data
        ])

    def notch_filter(self, data, Q=30):
        """Remove configured power-line interference, normally 60 Hz."""

        nyquist = self.fs / 2
        if not 0 < self.notch_freq < nyquist:
            raise ValueError("Notch frequency must be above 0 Hz and below Nyquist.")
        freq = self.notch_freq / nyquist

        b, a = signal.iirnotch(freq, Q)

        if data.ndim == 1:
            return filtfilt(b, a, data)

        return np.array([
            filtfilt(b, a, channel)
            for channel in data
        ])

    def normalize(self, data):
        """Apply z-score normalization independently to each channel."""

        if data.ndim == 1:
            return (
                data - np.mean(data)
            ) / (np.std(data) + 1e-8)

        return np.array([
            (channel - np.mean(channel))
            / (np.std(channel) + 1e-8)
            for channel in data
        ])

    def remove_artifacts(self, data, threshold=5):
        """Clip extreme normalized values to the configured threshold."""

        return np.clip(
            data,
            -threshold,
            threshold,
        )

    def preprocess(self, data):
        """Apply bandpass, notch, z-score normalization, then clipping."""

        # 1. Bandpass filter
        data = self.bandpass_filter(data)

        # 2. Notch filter
        data = self.notch_filter(data)

        # 3. Z-score normalization
        data = self.normalize(data)

        # 4. Artifact clipping
        data = self.remove_artifacts(data)

        return data
