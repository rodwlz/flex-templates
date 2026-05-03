from pathlib import Path
from lib.core.interfaces import SimpleService


class FileAdapter(SimpleService):
    """
    Actions: read, list

    read(data: {path, columns?, limit?}) -> {rows, count}
    list(data: {path?}) -> {files, path}

    Supported formats: .csv, .json, .parquet, .xlsx
    Base path is set at construction to prevent traversal attacks.
    """

    def __init__(self, base_path: str = "."):
        self._base = Path(base_path).resolve()

    def read(self, data: dict) -> dict:
        import pandas as pd
        path = self._resolve(data["path"])
        readers = {
            ".csv": pd.read_csv,
            ".json": pd.read_json,
            ".parquet": pd.read_parquet,
            ".xlsx": pd.read_excel,
        }
        reader = readers.get(path.suffix.lower())
        if reader is None:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        df = reader(path)
        if cols := data.get("columns"):
            df = df[cols]
        if limit := data.get("limit"):
            df = df.head(limit)
        return {"rows": df.to_dict(orient="records"), "count": len(df)}

    def list(self, data: dict) -> dict:
        folder = self._resolve(data.get("path", "."))
        files = [f.name for f in folder.iterdir()
                 if f.suffix.lower() in {".csv", ".json", ".parquet", ".xlsx"}]
        return {"files": files, "path": str(folder)}

    def _resolve(self, rel_path: str) -> Path:
        full = (self._base / rel_path).resolve()
        if not str(full).startswith(str(self._base)):
            raise ValueError("Path traversal outside base_path is not allowed")
        return full
