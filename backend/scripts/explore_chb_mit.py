"""List EDF and annotation files for a local CHB-MIT dataset folder.

Example:
    .venv/bin/python scripts/explore_chb_mit.py \
      /Users/daffa/Downloads/chb-mit-scalp-eeg-database-1.0.0 chb01
"""

import sys
from pathlib import Path


def explore_dataset(dataset_path: str, patient_folder: str = "chb01") -> None:
    """Print the patient-folder and EDF/annotation structure without reading EEG."""
    root = Path(dataset_path)
    patient_path = root / patient_folder
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset folder does not exist: {root}")
    if not patient_path.is_dir():
        raise FileNotFoundError(f"Patient folder does not exist: {patient_path}")

    patient_folders = sorted(path.name for path in root.iterdir() if path.is_dir())
    edf_files = sorted(patient_path.glob("*.edf"))
    seizure_files = sorted(patient_path.glob("*.seizures"))
    other_files = sorted(
        path for path in patient_path.iterdir()
        if path.suffix not in {".edf", ".seizures"}
    )

    print(f"Patient folders ({len(patient_folders)}): {', '.join(patient_folders)}")
    print(f"\n{patient_folder} EDF files ({len(edf_files)}):")
    for path in edf_files:
        print(f"  {path.name}")
    print(f"\nSeizure annotation files ({len(seizure_files)}):")
    for path in seizure_files:
        print(f"  {path.name}")
    print(f"\nOther files ({len(other_files)}):")
    for path in other_files:
        print(f"  {path.name}")


if __name__ == "__main__":
    if not 2 <= len(sys.argv) <= 3:
        raise SystemExit("Usage: explore_chb_mit.py <dataset_path> [patient_folder]")
    explore_dataset(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else "chb01")
