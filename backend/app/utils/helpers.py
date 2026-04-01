from datetime import datetime, timezone
from typing import List, Any, Dict, Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def make_paginated_response(items: list, total: int, skip: int, limit: int) -> Dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total,
    }
