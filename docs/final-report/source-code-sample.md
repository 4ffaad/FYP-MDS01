# Appendix C — Representative encrypted-storage source sample

This sample contains 73 non-empty Python source lines (87 physical lines with blank separators) copied from `backend/app/services/storage_service.py`. It contains the caller-to-callee path `save_draft_upload → _encrypt_upload`, the runtime key lookup, owner-only file creation, and retained-artifact encryption/cleanup. Complete function docstrings are included. It demonstrates RTM requirement SEC-01: encrypting retained files and cleaning up temporary plaintext. It does not demonstrate authorization or case-level retention/deletion.

```python
    async def save_draft_upload(self, draft_id: str, upload: UploadFile) -> Path:
        """Encrypt a ZIP into short-lived private draft storage."""

        return await self._encrypt_upload(upload, self.draft_path(draft_id), max_bytes=MAX_UPLOAD_BYTES)

    async def _encrypt_upload(self, upload: UploadFile, destination: Path, *, max_bytes: int) -> Path:
        """Stream one upload through AES-GCM into an owner-only file."""

        total = 0
        nonce = secrets.token_bytes(_NONCE_BYTES)
        encryptor = Cipher(algorithms.AES(self._key()), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(self._associated_data(destination))
        try:
            with self._open_private_output(destination) as output:
                output.write(_BOUND_ENCRYPTED_MAGIC)
                output.write(nonce)
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise StorageError("Uploaded archive exceeds the size limit.")
                    output.write(encryptor.update(chunk))
                output.write(encryptor.finalize())
                output.write(encryptor.tag)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        os.chmod(destination, 0o600)
        return destination

    def _key(self) -> bytes:
        """Return the injected test key or the required runtime storage key."""

        try:
            return self.storage_key or read_base64_key(STORAGE_KEY_ENV)
        except CryptoError as exc:
            raise StorageError(str(exc)) from exc

    @staticmethod
    def _open_private_input(path: Path):
        """Open a regular private file without following a symlink."""

        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        return os.fdopen(os.open(path, flags), "rb")

    @staticmethod
    def _open_private_output(path: Path):
        """Create a new owner-only file without following a symlink."""

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        return os.fdopen(os.open(path, flags, 0o600), "wb")

    def store_encrypted_artifact(self, session_id: str, source_path: Path, name: str) -> Path:
        """Encrypt one retained derived artifact and return its private path.

        Parameters
        ----------
        session_id : str
            Opaque session identifier.
        source_path : pathlib.Path
            Temporary plaintext artifact to encrypt and remove on success.
        name : str
            Safe artifact basename, without a user-controlled path.

        Returns
        -------
        pathlib.Path
            Private encrypted artifact path.

        Raises
        ------
        StorageError
            Raised when the source is invalid or encryption fails.
        """

        if Path(name).name != name or not name:
            raise StorageError("Retained artifact name is invalid.")
        destination = self.directory(session_id, "retained") / f"{name}.enc"
        try:
            with self._open_private_input(Path(source_path)) as source, self._open_private_output(destination) as output:
                self._encrypt_stream(source, output, destination)
            os.chmod(destination, 0o600)
            return destination
        except Exception as exc:
            destination.unlink(missing_ok=True)
            raise StorageError("Retained artifact could not be encrypted.") from exc
        finally:
            Path(source_path).unlink(missing_ok=True)
```
