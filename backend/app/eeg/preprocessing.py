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
        """Configure the fixed EEG filtering and normalization pipeline.

        Parameters
        ----------
        sampling_rate : int
            Signal sampling rate in Hertz.
        low_freq : float
            Lower band-pass cutoff in Hertz.
        high_freq : float
            Upper band-pass cutoff in Hertz.
        notch_freq : float
            Power-line notch frequency in Hertz.
        """

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

        # Filter all channels in one SciPy call. The axis and filter
        # parameters are unchanged; this only removes Python-loop overhead.
        return filtfilt(b, a, data, axis=-1)

    def notch_filter(self, data, Q=30):
        """Remove configured power-line interference, normally 60 Hz."""

        nyquist = self.fs / 2
        if not 0 < self.notch_freq < nyquist:
            raise ValueError("Notch frequency must be above 0 Hz and below Nyquist.")
        freq = self.notch_freq / nyquist

        b, a = signal.iirnotch(freq, Q)

        if data.ndim == 1:
            return filtfilt(b, a, data)

        return filtfilt(b, a, data, axis=-1)

    def normalize(self, data):
        """Apply z-score normalization independently to each channel."""

        if data.ndim == 1:
            return (
                data - np.mean(data)
            ) / (np.std(data) + 1e-8)

        mean = np.mean(data, axis=-1, keepdims=True)
        standard_deviation = np.std(data, axis=-1, keepdims=True)
        return (data - mean) / (standard_deviation + 1e-8)

    def remove_artifacts(self, data, threshold=5):
        """Clip extreme normalized values to the configured threshold."""

        return np.clip(
            data,
            -threshold,
            threshold,
        )

    def preprocess(self, data):
        """Apply bandpass, notch, z-score normalization, then clipping."""

        if not np.isfinite(data).all():
            raise ValueError("EEG signal contains non-finite values.")

        # 1. Bandpass filter
        data = self.bandpass_filter(data)

        # 2. Notch filter
        data = self.notch_filter(data)

        # 3. Z-score normalization
        data = self.normalize(data)

        # 4. Artifact clipping
        data = self.remove_artifacts(data)

        if not np.isfinite(data).all():
            raise ValueError("EEG preprocessing produced non-finite values.")

        return data
