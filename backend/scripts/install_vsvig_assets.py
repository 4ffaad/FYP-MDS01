"""Install the pinned VSViG and pose assets outside the repository.

The installer downloads only files whose source revisions and SHA-256 digests
are pinned in ``backend.app.video_detection.contract``. It never downloads
patient media or executes downloaded Python during installation.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Support both ``python backend/scripts/...py`` and ``python -m ...``.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.video_detection.contract import (
    LICENSES,
    POSE_COMMIT,
    POSE_REPOSITORY,
    POSE_SOURCES,
    UPSTREAM_ARTIFACTS,
    UPSTREAM_COMMIT,
    UPSTREAM_REPOSITORY,
    UPSTREAM_SOURCES,
    digest,
)
from backend.scripts.video_contract import template

MAX_DOWNLOAD_BYTES = 128 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 120


def _downloads() -> dict[str, tuple[str, str, str, str]]:
    """Return destination, repository, revision, source path, and digest."""

    files: dict[str, tuple[str, str, str, str]] = {}
    for destination, expected in UPSTREAM_SOURCES.items():
        files[destination] = (
            UPSTREAM_REPOSITORY,
            UPSTREAM_COMMIT,
            destination.removeprefix("vsvig/"),
            expected,
        )
    for destination, expected in UPSTREAM_ARTIFACTS.items():
        files[destination] = (UPSTREAM_REPOSITORY, UPSTREAM_COMMIT, destination, expected)
    for destination, expected in POSE_SOURCES.items():
        files[destination] = (
            POSE_REPOSITORY,
            POSE_COMMIT,
            destination.removeprefix("openpose/"),
            expected,
        )
    for destination, expected in LICENSES.items():
        repository, revision, source = (
            (UPSTREAM_REPOSITORY, UPSTREAM_COMMIT, "LICENSE")
            if destination.startswith("vsvig/")
            else (POSE_REPOSITORY, POSE_COMMIT, "LICENSE")
        )
        files[destination] = (repository, revision, source, expected)
    return files


def _sha256(path: Path) -> str:
    return digest(path)


def _reject_symlink_components(path: Path, *, stop_at: Path | None = None) -> None:
    """Reject symlink aliases along a controlled path before writing."""

    current = path
    while True:
        if current.is_symlink():
            raise RuntimeError("asset paths must not contain symlinks")
        if stop_at is not None:
            if current == stop_at:
                return
            if stop_at not in current.parents:
                raise RuntimeError("asset path escaped its configured root")
        elif current == current.parent:
            return
        current = current.parent


def _download_verified(
    destination: Path,
    repository: str,
    revision: str,
    source_path: str,
    expected_digest: str,
    *,
    root: Path | None = None,
) -> str:
    """Download one file to a same-directory temporary file and verify it."""

    _reject_symlink_components(destination, stop_at=root)
    if destination.exists() and not destination.is_file():
        raise RuntimeError(f"asset destination is not a regular file: {destination.name}")
    if destination.is_file() and _sha256(destination) == expected_digest:
        return "verified existing"

    url = f"{repository}/raw/{revision}/{source_path}"
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or parsed_url.netloc.lower() != "github.com":
        raise RuntimeError("pinned asset sources must use the official HTTPS GitHub host")
    request = Request(url, headers={"User-Agent": "MDS01-VSViG-installer/1"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        # The URL is constructed only from pinned constants and restricted above.
        with urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:  # nosec B310
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise RuntimeError(f"download exceeds the safety limit: {destination.name}")
                    temporary.write(chunk)
    except (HTTPError, URLError, OSError) as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise RuntimeError(f"could not download pinned asset {destination.name}") from exc
    except RuntimeError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise

    try:
        if temporary_path is None:
            raise RuntimeError(f"download produced no file: {destination.name}")
        if _sha256(temporary_path) != expected_digest:
            raise RuntimeError(f"SHA-256 mismatch for pinned asset {destination.name}")
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return "downloaded and verified"


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        temporary.write(content)
        temporary.flush()
        os.fchmod(temporary.fileno(), 0o644)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _update_env(path: Path, values: dict[str, str]) -> None:
    """Upsert non-secret runtime paths/hashes without rotating other settings."""

    path = _checked_env_path(path)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = original.splitlines()
    found: set[str] = set()
    output: list[str] = []
    for line in lines:
        key, separator, _ = line.partition("=")
        if separator and key in values:
            output.append(f"{key}={values[key]}")
            found.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in found:
            output.append(f"{key}={value}")
    _write_atomic(path, "\n".join(output).rstrip() + "\n")
    os.chmod(path, 0o600)


def _checked_env_path(path: Path) -> Path:
    """Return an environment path without resolving away its final symlink."""

    path = Path(os.path.abspath(path.expanduser()))
    if path.is_symlink():
        raise RuntimeError("the environment file must be a regular file, not a symlink or directory")
    _reject_symlink_components(path)
    if path.exists() and not path.is_file():
        raise RuntimeError("the environment file must be a regular file, not a symlink or directory")
    return path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def install(asset_dir: Path, *, approve_source_contract: bool, env_file: Path | None) -> dict[str, str]:
    """Install and manifest the pinned external runtime."""

    checked_env_file = _checked_env_path(env_file) if env_file is not None else None
    asset_dir = asset_dir.expanduser()
    if not asset_dir.is_absolute():
        raise RuntimeError("--asset-dir must be an absolute path")
    _reject_symlink_components(asset_dir)
    if asset_dir.exists() and not asset_dir.is_dir():
        raise RuntimeError("--asset-dir must be a directory")
    asset_dir = Path(os.path.abspath(asset_dir))
    repo_root = _repo_root()
    if asset_dir == repo_root or repo_root in asset_dir.parents:
        raise RuntimeError("keep VSViG assets outside the repository")

    asset_dir.mkdir(parents=True, exist_ok=True)
    for relative, (repository, revision, source, expected) in _downloads().items():
        status = _download_verified(
            asset_dir / relative,
            repository,
            revision,
            source,
            expected,
            root=asset_dir,
        )
        print(f"{status}: {relative}")

    contract = template(asset_dir, reviewed=approve_source_contract)
    contract_path = asset_dir / "contract.json"
    _write_atomic(contract_path, json.dumps(contract, indent=2) + "\n")
    contract_digest = _sha256(contract_path)
    values = {
        "VSVIG_ASSET_DIR": str(asset_dir),
        "VSVIG_CONTRACT_SHA256": contract_digest,
    }
    if checked_env_file is not None:
        _update_env(checked_env_file, values)
        print(f"Updated VSViG settings in {checked_env_file}")
    return {**values, "reviewed": str(approve_source_contract).lower()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset-dir",
        type=Path,
        required=True,
        help="absolute directory outside this repository for the model bundle",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="optional .env file to update with VSVIG_ASSET_DIR and its manifest hash",
    )
    parser.add_argument(
        "--approve-source-contract",
        action="store_true",
        help="enable the source/runtime-reviewed contract; this is not clinical validation",
    )
    args = parser.parse_args()
    try:
        values = install(
            args.asset_dir,
            approve_source_contract=args.approve_source_contract,
            env_file=args.env_file,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Asset bundle: {values['VSVIG_ASSET_DIR']}")
    print(f"Contract SHA-256: {values['VSVIG_CONTRACT_SHA256']}")
    print(f"Source/runtime contract reviewed: {values['reviewed']}")
    if values["reviewed"] != "true":
        print("Inference remains fail-closed until --approve-source-contract is used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
