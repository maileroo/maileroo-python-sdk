from __future__ import annotations

import json
import re
import secrets
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import requests

from .attachment import Attachment
from .email_address import EmailAddress


ApiAssocValue = Union[str, int, float, bool]
ApiAssocMap = Mapping[str, ApiAssocValue]

API_BASE_URL = "https://smtp.maileroo.com/api/v2/"
MAX_ASSOCIATIVE_MAP_KEY_LENGTH = 128
MAX_ASSOCIATIVE_MAP_VALUE_LENGTH = 768
MAX_SUBJECT_LENGTH = 255
REFERENCE_ID_LENGTH = 24  # hex chars


class MailerooClient:
    def __init__(self, api_key: str, timeout: int = 30) -> None:
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise ValueError("API key must be a non-empty string.")
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("Timeout must be a positive integer.")
        self._api_key = api_key
        self._timeout = timeout

    # ---------- Utilities ----------
    @staticmethod
    def get_reference_id() -> str:
        # 24 hex chars => 12 random bytes -> hex
        return secrets.token_hex(REFERENCE_ID_LENGTH // 2)

    _REF_RE = re.compile(r"^[0-9a-fA-F]{" + str(REFERENCE_ID_LENGTH) + r"}$")

    def _validate_reference_id(self, reference_id: str) -> str:
        if not isinstance(reference_id, str):
            raise ValueError("reference_id must be a string.")
        if reference_id != reference_id.strip():
            raise ValueError("reference_id must not contain whitespace.")
        if not self._REF_RE.match(reference_id):
            raise ValueError(
                f"reference_id must be a {REFERENCE_ID_LENGTH}-character hexadecimal string."
            )
        return reference_id

    @staticmethod
    def _is_ok_value(v: Any) -> bool:
        return isinstance(v, (str, int, float, bool))

    def _validate_assoc_map(self, m: Mapping[str, Any], label: str) -> None:
        for k, v in m.items():
            if not isinstance(k, str) or not self._is_ok_value(v):
                raise ValueError(f"{label} must be an associative mapping with string keys and simple values.")
            if len(k) > MAX_ASSOCIATIVE_MAP_KEY_LENGTH or len(str(v)) > MAX_ASSOCIATIVE_MAP_VALUE_LENGTH:
                raise ValueError(
                    f"{label} key must not exceed {MAX_ASSOCIATIVE_MAP_KEY_LENGTH} chars and value must not exceed {MAX_ASSOCIATIVE_MAP_VALUE_LENGTH} chars."
                )

    def _normalize_email_field(self, field: Any) -> EmailAddress:
        if isinstance(field, EmailAddress):
            return field
        raise ValueError("Email field must be an instance of EmailAddress.")

    def _normalize_email_field_or_array(self, value: Any) -> Union[EmailAddress, List[EmailAddress]]:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [self._normalize_email_field(v) for v in value]
        return self._normalize_email_field(value)

    @staticmethod
    def _email_to_arrays(e: Optional[Union[EmailAddress, List[EmailAddress]]]) -> Optional[Union[dict, List[dict]]]:
        if e is None:
            return None
        if isinstance(e, list):
            return [x.to_dict() for x in e]
        return e.to_dict()

    def _get_parsed_email_items(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        required = ("from", "to")
        for f in required:
            if f not in data:
                raise ValueError(f"Field {f} is required.")

        parsed: Dict[str, Any] = {}
        d = dict(data)

        d["from"] = self._normalize_email_field(d["from"])
        d["to"] = self._normalize_email_field_or_array(d["to"])

        for opt in ("cc", "bcc", "reply_to"):
            if opt in d:
                d[opt] = self._normalize_email_field_or_array(d[opt])

        parsed["from"] = self._email_to_arrays(d.get("from"))
        parsed["to"] = self._email_to_arrays(d.get("to"))
        parsed["cc"] = self._email_to_arrays(d.get("cc"))
        parsed["bcc"] = self._email_to_arrays(d.get("bcc"))
        parsed["reply_to"] = self._email_to_arrays(d.get("reply_to"))
        return parsed

    # ---------- Payload builders ----------
    def _build_base_payload(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        payload = self._get_parsed_email_items(data)

        subj = data.get("subject")
        if not isinstance(subj, str) or subj.strip() == "" or len(subj) > MAX_SUBJECT_LENGTH:
            raise ValueError(f"Subject must be a non-empty string with a maximum length of {MAX_SUBJECT_LENGTH} characters.")
        payload["subject"] = subj

        if "tracking" in data:
            if not isinstance(data["tracking"], bool):
                raise ValueError("Tracking must be a boolean value.")
            payload["tracking"] = data["tracking"]

        if isinstance(data.get("tags"), Mapping):
            self._validate_assoc_map(data["tags"], "tags")
            payload["tags"] = dict(data["tags"])

        if isinstance(data.get("headers"), Mapping):
            self._validate_assoc_map(data["headers"], "headers")
            payload["headers"] = dict(data["headers"])

        if "attachments" in data:
            atts = data["attachments"]
            if not isinstance(atts, Sequence):
                raise ValueError("attachments must be a list of Attachment.")
            payload["attachments"] = []
            for a in atts:
                if not isinstance(a, Attachment):
                    raise ValueError("Each attachment must be an instance of Attachment.")
                payload["attachments"].append(a.to_dict())

        if isinstance(data.get("scheduled_at"), str):
            payload["scheduled_at"] = data["scheduled_at"]

        if "reference_id" in data:
            payload["reference_id"] = self._validate_reference_id(str(data["reference_id"]))
        else:
            payload["reference_id"] = self.get_reference_id()

        return payload

    @staticmethod
    def _validate_template_data(template_data: Any) -> Dict[str, Any]:
        if template_data in (None, "", []):
            return {}
        if not isinstance(template_data, Mapping):
            raise ValueError("template_data must be a mapping if provided.")
        for k in template_data.keys():
            if not isinstance(k, str):
                raise ValueError("template_data keys must be strings.")
        return dict(template_data)

    # ---------- Public API ----------
    def send_basic_email(self, data: Mapping[str, Any]) -> str:
        payload = self._build_base_payload(data)
        if "html" not in data and "plain" not in data:
            raise ValueError("Either html or plain body is required.")
        payload["html"] = data.get("html")
        payload["plain"] = data.get("plain")
        resp = self._send_request("POST", "emails", payload)
        if resp.get("success"):
            return resp["data"]["reference_id"]
        raise RuntimeError(f'The API returned an error: {resp.get("message", "Unknown")}')

    def send_templated_email(self, data: Mapping[str, Any]) -> str:
        payload = self._build_base_payload(data)
        tid = data.get("template_id")
        if not (isinstance(tid, (int, str))):
            raise ValueError("template_id must be an integer or a string.")
        payload["template_id"] = int(tid)
        if "template_data" in data:
            payload["template_data"] = self._validate_template_data(data["template_data"])
        resp = self._send_request("POST", "emails/template", payload)
        if resp.get("success"):
            return resp["data"]["reference_id"]
        raise RuntimeError(f'The API returned an error: {resp.get("message", "Unknown")}')

    def send_bulk_emails(self, data: Mapping[str, Any]) -> List[str]:
        subj = data.get("subject")
        if not isinstance(subj, str) or subj.strip() == "" or len(subj) > MAX_SUBJECT_LENGTH:
            raise ValueError(f"Subject must be a non-empty string with a maximum length of {MAX_SUBJECT_LENGTH} characters.")

        has_html = isinstance(data.get("html"), str)
        has_plain = isinstance(data.get("plain"), str)
        tid = data.get("template_id")
        has_template = isinstance(tid, (int, str))

        if (not has_html and not has_plain) and not has_template:
            raise ValueError("You must provide either html, plain, or template_id.")
        if has_template and (has_html or has_plain):
            raise ValueError("template_id cannot be combined with html or plain.")

        messages = data.get("messages")
        if not isinstance(messages, Sequence) or len(messages) == 0:
            raise ValueError("messages must be a non-empty list.")
        if len(messages) > 500:
            raise ValueError("messages cannot contain more than 500 items.")

        payload: Dict[str, Any] = {"subject": subj}
        if has_html:
            payload["html"] = data["html"]
        if has_plain:
            payload["plain"] = data["plain"]
        if has_template:
            payload["template_id"] = int(tid)

        if "tracking" in data:
            if not isinstance(data["tracking"], bool):
                raise ValueError("Tracking must be a boolean value.")
            payload["tracking"] = data["tracking"]

        if isinstance(data.get("tags"), Mapping):
            self._validate_assoc_map(data["tags"], "tags")
            payload["tags"] = dict(data["tags"])

        if isinstance(data.get("headers"), Mapping):
            self._validate_assoc_map(data["headers"], "headers")
            payload["headers"] = dict(data["headers"])

        if "attachments" in data:
            atts = data["attachments"]
            if not isinstance(atts, Sequence):
                raise ValueError("attachments must be a list of Attachment.")
            payload["attachments"] = []
            for a in atts:
                if not isinstance(a, Attachment):
                    raise ValueError("Each attachment must be an instance of Attachment.")
                payload["attachments"].append(a.to_dict())

        payload["messages"] = self._normalize_bulk_messages(messages)

        resp = self._send_request("POST", "emails/bulk", payload)
        if isinstance(resp, dict) and resp.get("success") and "data" in resp:
            return resp["data"]["reference_ids"]
        raise RuntimeError(f'The API returned an error: {resp.get("message", "Unknown")}')

    def delete_scheduled_email(self, reference_id: str) -> bool:
        ref = self._validate_reference_id(reference_id)
        resp = self._send_request("DELETE", f"emails/scheduled/{ref}")
        if isinstance(resp, dict) and resp.get("success"):
            return True
        raise RuntimeError(f'The API returned an error: {resp.get("message", "Unknown")}')

    def get_scheduled_emails(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        if not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer (>= 1).")
        if not isinstance(per_page, int) or per_page < 1:
            raise ValueError("per_page must be a positive integer (>= 1).")
        if per_page > 100:
            raise ValueError("per_page cannot be greater than 100.")

        resp = self._send_request("GET", "emails/scheduled", {"page": page, "per_page": per_page})
        if isinstance(resp, dict) and resp.get("success") and "data" in resp:
            return resp["data"]
        raise RuntimeError(f'The API returned an error: {resp.get("message", "Unknown")}')

    # ---------- Internals ----------
    def _normalize_bulk_messages(self, messages: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for idx, msg in enumerate(messages):
            if not isinstance(msg, Mapping):
                raise ValueError(f"Each message must be a mapping (message index {idx}).")
            if "from" not in msg or "to" not in msg:
                raise ValueError(f"Each message must include 'from' and 'to' (message index {idx}).")

            from_val = self._normalize_email_field(msg["from"])
            to_val = self._normalize_email_field_or_array(msg["to"])
            cc_val = self._normalize_email_field_or_array(msg["cc"]) if "cc" in msg else None
            bcc_val = self._normalize_email_field_or_array(msg["bcc"]) if "bcc" in msg else None
            reply_val = self._normalize_email_field_or_array(msg["reply_to"]) if "reply_to" in msg else None

            item: Dict[str, Any] = {
                "from": self._email_to_arrays(from_val),
                "to": self._email_to_arrays(to_val),
                "cc": self._email_to_arrays(cc_val),
                "bcc": self._email_to_arrays(bcc_val),
                "reply_to": self._email_to_arrays(reply_val),
            }

            if "reference_id" in msg:
                item["reference_id"] = self._validate_reference_id(str(msg["reference_id"]))
            else:
                item["reference_id"] = self.get_reference_id()

            if "template_data" in msg:
                item["template_data"] = self._validate_template_data(msg["template_data"])

            out.append(item)
        return out

    def _send_request(self, method: str, endpoint: str, data: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        method = method.upper()
        url = API_BASE_URL + endpoint.lstrip("/")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "maileroo-python-sdk/1.0",
        }

        try:
            if method == "GET":
                r = requests.get(url, headers=headers, params=(data or {}), timeout=self._timeout)
            else:
                payload = json.dumps(data or {})
                r = requests.request(method, url, headers=headers, data=payload, timeout=self._timeout)
        except requests.RequestException as e:
            raise RuntimeError(f"HTTP request failed: {e}") from e

        text = r.text or ""
        try:
            decoded = r.json() if text else {}
        except ValueError:
            raise RuntimeError("The API response is not valid JSON.")

        if not isinstance(decoded, dict) or "success" not in decoded or not isinstance(decoded["success"], bool):
            raise RuntimeError('The API response is missing the "success" field.')

        if not decoded.get("message"):
            decoded["message"] = "Unknown"

        return decoded
