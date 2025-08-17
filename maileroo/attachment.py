from __future__ import annotations

import base64
import io
import mimetypes
from dataclasses import dataclass
from typing import Optional

try:
    import magic as _python_magic
except Exception:  # pragma: no cover
    _python_magic = None


def _detect_mime_from_buffer(buf: bytes) -> Optional[str]:
    if _python_magic is None:
        return None
    try:
        m = _python_magic.Magic(mime=True)
        t = m.from_buffer(buf)
        return t if isinstance(t, str) and t.strip() else None
    except Exception:
        return None


def _detect_mime_from_path(path: str, sample: Optional[bytes]) -> Optional[str]:
    # Try libmagic on the file bytes first
    if sample:
        t = _detect_mime_from_buffer(sample)
        if t:
            return t
    # Fallback: extension map
    t, _ = mimetypes.guess_type(path)
    return t


@dataclass(frozen=True)
class Attachment:
    file_name: str
    content: str  # base64
    content_type: str = "application/octet-stream"
    inline: bool = False

    def __post_init__(self):
        if not isinstance(self.file_name, str) or self.file_name == "":
            raise ValueError("file_name is required.")
        if not isinstance(self.content, str) or self.content == "":
            raise ValueError("content must be a non-empty base64 string.")
        # quick base64 sanity check
        try:
            base64.b64decode(self.content, validate=True)
        except Exception as e:
            raise ValueError("content is not valid base64.") from e
        if not isinstance(self.inline, bool):
            raise ValueError("inline must be a boolean.")

    @staticmethod
    def from_content(
        file_name: str,
        content: bytes | str,
        content_type: Optional[str] = None,
        inline: bool = False,
        is_base64: bool = False,
    ) -> "Attachment":
        if isinstance(content, str):
            raw = content.encode("utf-8") if not is_base64 else None
        else:
            raw = content

        if is_base64:
            if not isinstance(content, str):
                raise ValueError("When is_base64=True, content must be a base64 string.")
            try:
                raw = base64.b64decode(content, validate=True)
            except Exception as e:
                raise ValueError("Invalid base64 content provided.") from e

        assert isinstance(raw, (bytes, bytearray))
        detected = content_type or _detect_mime_from_buffer(raw) or "application/octet-stream"
        b64 = base64.b64encode(raw).decode("ascii")
        return Attachment(file_name=file_name, content=b64, content_type=detected, inline=inline)

    @staticmethod
    def from_stream(
        file_name: str,
        stream: io.BufferedIOBase | io.RawIOBase | io.BytesIO,
        content_type: Optional[str] = None,
        inline: bool = False,
    ) -> "Attachment":
        if not hasattr(stream, "read"):
            raise ValueError("stream must be a readable file-like object.")
        try:
            if hasattr(stream, "seek"):
                stream.seek(0)
            binary = stream.read()
        except Exception as e:
            raise RuntimeError("Failed to read from stream.") from e
        if not isinstance(binary, (bytes, bytearray)):
            raise RuntimeError("Stream did not produce bytes.")
        detected = content_type or _detect_mime_from_buffer(binary) or "application/octet-stream"
        b64 = base64.b64encode(binary).decode("ascii")
        return Attachment(file_name=file_name, content=b64, content_type=detected, inline=inline)

    @staticmethod
    def from_file(
        path: str,
        content_type: Optional[str] = None,
        inline: bool = False,
    ) -> "Attachment":
        import os

        if not isinstance(path, str) or path == "" or not (os.path.isfile(path) and os.access(path, os.R_OK)):
            raise ValueError("path must be a readable file.")
        file_name = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                binary = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {path}") from e

        detected = (
            content_type
            or _detect_mime_from_path(path, binary)
            or _detect_mime_from_buffer(binary)
            or "application/octet-stream"
        )
        b64 = base64.b64encode(binary).decode("ascii")
        return Attachment(file_name=file_name, content=b64, content_type=detected, inline=inline)

    def to_dict(self) -> dict:
        return {
            "file_name": self.file_name,
            "content_type": self.content_type or "application/octet-stream",
            "content": self.content,
            "inline": self.inline,
        }
