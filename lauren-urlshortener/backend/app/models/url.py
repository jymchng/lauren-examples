"""URL shortener models — dataclasses only, no pydantic."""

from __future__ import annotations

import dataclasses
from typing import TypedDict


@dataclasses.dataclass
class CreateUrlRequest:
    url: str
    custom_code: str = ""
    title: str = ""
    expires_at: str = ""


@dataclasses.dataclass
class UpdateUrlRequest:
    title: str = ""
    expires_at: str = ""


@dataclasses.dataclass
class UrlRecord:
    id: str
    code: str
    original_url: str
    title: str
    created_at: str
    updated_at: str
    expires_at: str
    is_active: bool
    click_count: int


class ClickRecord(TypedDict):
    id: str
    url_code: str
    clicked_at: str
    ip_address: str
    user_agent: str
    referer: str


def row_to_url_record(row: dict) -> UrlRecord:
    return UrlRecord(
        id=row["id"],
        code=row["code"],
        original_url=row["original_url"],
        title=row.get("title") or "",
        created_at=row.get("created_at") or "",
        updated_at=row.get("updated_at") or "",
        expires_at=row.get("expires_at") or "",
        is_active=bool(row.get("is_active", 1)),
        click_count=int(row.get("click_count", 0)),
    )
