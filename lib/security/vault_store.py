"""File I/O for encrypted vault storage."""
import json
import os
from pathlib import Path


class VaultStore:
    """Reads/writes encrypted vault blob from `.secrets/vault.json`."""

    def __init__(self, path: str = ".secrets/vault.json"):
        self._path = path
        self._dir = os.path.dirname(path) or "."

    def exists(self) -> bool:
        """Check if vault file exists."""
        return os.path.isfile(self._path)

    def load(self) -> str:
        """Read encrypted blob from disk."""
        if not self.exists():
            raise FileNotFoundError(f"Vault not found at {self._path}")
        with open(self._path, "r") as f:
            data = json.load(f)
            # The encrypted vault data is stored under 'vault' key
            return data.get("vault", "")

    def save(self, blob: str) -> None:
        """Write encrypted vault data to disk as JSON."""
        if not blob:
            raise ValueError("Cannot save empty blob")
        
        Path(self._dir).mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self._path, "w") as f:
                # Save as JSON with encrypted vault data
                json.dump({"vault": blob}, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except IOError as e:
            raise RuntimeError(f"Failed to write vault file: {e}")

    def delete(self) -> None:
        """Delete vault file."""
        if self.exists():
            os.remove(self._path)
