import unicodedata
from pathlib import Path


def safe_storage_key_name(file_name: str | None) -> str:
    """Sanitize a user-supplied filename for safe use inside a storage key.

    Keeps only the basename so a name containing path separators (``/`` or
    ``\\``) or ``..`` cannot introduce unexpected key nesting, NFC-normalizes
    unicode, and drops control characters. The original display name should be
    stored separately (e.g. on the DB row); this only protects the object key.
    """
    if not file_name:
        return "unnamed"
    name = Path(file_name.replace("\\", "/")).name
    name = unicodedata.normalize("NFC", name)
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = name.strip()
    if name in {".", ".."}:
        return "unnamed"
    return name or "unnamed"


def split_file_params(filepath: str) -> tuple[str, str, str]:
    file_path = Path(filepath)
    folder_path = str(file_path.parent)
    filename = file_path.stem
    extension = file_path.suffix.replace(".", "")
    return folder_path, filename, extension


def get_filename_from_path(file_path: str | None) -> str | None:
    if not file_path:
        return None
    return Path(file_path).name


def remove_slash_from_path(file_path: str) -> str:
    if file_path and file_path.startswith("/"):
        return file_path[1:]
    return file_path


def remove_extension(filename: str) -> str:
    if filename and "." in filename:
        return filename.rsplit(".", 1)[0]
    return filename
