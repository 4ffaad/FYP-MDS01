import sys
from pathlib import Path

import pyedflib
import mne


def inspect_edf(file_path: str):
    path = Path(file_path)

    if not path.exists():
        print(f"ERROR: File does not exist: {path}")
        return

    if path.suffix.lower() != ".edf":
        print(f"WARNING: File does not have .edf extension: {path}")

    print("=" * 70)
    print("EDF FILE INSPECTION")
    print("=" * 70)

    print(f"\nFile: {path.name}")
    print(f"Path: {path.resolve()}")
    print(f"Size: {path.stat().st_size / (1024 * 1024):.2f} MB")

    # ---------------------------------------------------------
    # PYEDFLIB: Raw EDF header information
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("1. EDF HEADER / PATIENT INFORMATION")
    print("=" * 70)

    try:
        with pyedflib.EdfReader(str(path)) as f:

            print(f"\nPatient code:       {f.getPatientCode()}")
            print(f"Patient name:       {f.getPatientName()}")
            print(f"Recording additional: {f.getRecordingAdditional()}")
            print(f"Technician:         {f.getTechnician()}")
            print(f"Equipment:          {f.getEquipment()}")

            start_date = f.getStartdatetime()

            print(f"Start datetime:     {start_date}")

            print(f"\nNumber of signals:  {f.signals_in_file}")
            print(f"File duration:      {f.file_duration:.2f} seconds")

            print("\n" + "-" * 70)
            print("CHANNEL INFORMATION")
            print("-" * 70)

            for i in range(f.signals_in_file):
                label = f.getLabel(i)
                sample_frequency = f.getSampleFrequency(i)
                physical_min = f.getPhysicalMinimum(i)
                physical_max = f.getPhysicalMaximum(i)
                digital_min = f.getDigitalMinimum(i)
                digital_max = f.getDigitalMaximum(i)

                print(f"\nChannel {i + 1}")
                print(f"  Label:              {label}")
                print(f"  Sampling frequency: {sample_frequency} Hz")
                print(f"  Physical range:     {physical_min} → {physical_max}")
                print(f"  Digital range:      {digital_min} → {digital_max}")

    except Exception as e:
        print(f"\nPyEDFlib ERROR: {e}")

    # ---------------------------------------------------------
    # MNE: EEG structure and annotations
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("2. MNE EEG INFORMATION")
    print("=" * 70)

    try:
        raw = mne.io.read_raw_edf(
            str(path),
            preload=False,
            verbose=False
        )

        print("\nChannel names:")
        for i, channel in enumerate(raw.ch_names, start=1):
            print(f"  {i:02d}. {channel}")

        print(f"\nNumber of channels: {len(raw.ch_names)}")
        print(f"Sampling frequency: {raw.info['sfreq']} Hz")
        print(f"Number of samples:  {raw.n_times}")
        print(f"Duration:            {raw.times[-1]:.2f} seconds")

        print(f"\nMeasurement date:    {raw.info['meas_date']}")
        print(f"Subject information: {raw.info['subject_info']}")

        print("\n" + "-" * 70)
        print("ANNOTATIONS")
        print("-" * 70)

        if len(raw.annotations) == 0:
            print("No annotations found.")
        else:
            print(f"Number of annotations: {len(raw.annotations)}")

            for i, annotation in enumerate(raw.annotations):
                print(
                    f"\nAnnotation {i + 1}:"
                    f"\n  Onset:      {annotation['onset']} sec"
                    f"\n  Duration:   {annotation['duration']} sec"
                    f"\n  Description: {annotation['description']}"
                )

    except Exception as e:
        print(f"\nMNE ERROR: {e}")

    print("\n" + "=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("\nUsage:")
        print("  python scripts/inspect_edf.py <path_to_edf>")
        print("\nExample:")
        print("  python scripts/inspect_edf.py data/chb02_16.edf")
        sys.exit(1)

    inspect_edf(sys.argv[1])