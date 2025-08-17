from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class EmailAddress:
    address: str
    display_name: Optional[str] = None

    def __post_init__(self):
        addr = self.address
        if not isinstance(addr, str) or addr.strip() == "":
            raise ValueError("Email address must be a non-empty string.")
        if not _EMAIL_RE.match(addr):
            raise ValueError(f"Invalid email address format: {addr}")
        if self.display_name is not None:
            if not isinstance(self.display_name, str) or self.display_name.strip() == "":
                raise ValueError("Display name must be a non-empty string or None.")

    def to_dict(self) -> dict:
        d = {"address": self.address}
        if self.display_name is not None:
            d["display_name"] = self.display_name
        return d
