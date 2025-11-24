from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Iterable, Tuple

from ..config import settings
from ..logging_config import logger

try:  # Optional dependency
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # noqa: BLE001
    QdrantClient = None  # type: ignore
    qmodels = None  # type: ignore

# Limits
MAX_QDRANT_VECTORS_PER_USER = 300
MAX_QDRANT_VECTORS_PER_DIALOG = 150
QDRANT_VECTOR_TTL_DAYS = 90

# Collections we expect (best-effort; skip if absent)
QDRANT_COLLECTIONS: tuple[str, ...] = ("user_memory", "dialog_summaries")


def get_qdrant_client() -> QdrantClient | None:
    if QdrantClient is None:
        return None
    if not settings.qdrant_url:
        return None
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def _parse_ts(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except Exception:  # noqa: BLE001
            return 0.0
    return 0.0


def _trim_group(
    client: QdrantClient,
    collection: str,
    points: Iterable,
    limit: int,
) -> int:
    sorted_points = sorted(points, key=lambda p: _parse_ts((p.payload or {}).get("created_at", 0)))
    extra = max(0, len(sorted_points) - limit)
    if extra <= 0:
        return 0
    to_delete = [p.id for p in sorted_points[:extra]]
    if not to_delete:
        return 0
    client.delete(collection_name=collection, points_selector=qmodels.PointIdsList(points=to_delete))
    return len(to_delete)


def trim_collection_limits(client: QdrantClient, collection: str) -> Tuple[int, int]:
    """
    Returns (deleted_by_user, deleted_by_dialog)
    """
    if qmodels is None:
        return (0, 0)

    deleted_user = 0
    deleted_dialog = 0
    scroll_filter = None
    offset = None
    all_points = []
    while True:
        batch, offset = client.scroll(
            collection_name=collection,
            scroll_filter=scroll_filter,
            with_vectors=False,
            with_payload=True,
            limit=256,
            offset=offset,
        )
        all_points.extend(batch)
        if offset is None:
            break

    groups_by_user = {}
    groups_by_dialog = {}
    for p in all_points:
        payload = p.payload or {}
        user_id = payload.get("user_id")
        dialog_id = payload.get("dialog_id")
        if user_id is not None:
            groups_by_user.setdefault(user_id, []).append(p)
        if dialog_id is not None:
            groups_by_dialog.setdefault(dialog_id, []).append(p)

    for pts in groups_by_user.values():
        deleted_user += _trim_group(client, collection, pts, MAX_QDRANT_VECTORS_PER_USER)
    for pts in groups_by_dialog.values():
        deleted_dialog += _trim_group(client, collection, pts, MAX_QDRANT_VECTORS_PER_DIALOG)
    return deleted_user, deleted_dialog


def trim_collection_ttl(client: QdrantClient, collection: str) -> int:
    if qmodels is None:
        return 0
    cutoff_ts = (datetime.utcnow() - timedelta(days=QDRANT_VECTOR_TTL_DAYS)).timestamp()
    scroll_filter = qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="created_at",
                range=qmodels.Range(lte=cutoff_ts),
            )
        ]
    )
    deleted = 0
    offset = None
    while True:
        batch, offset = client.scroll(
            collection_name=collection,
            scroll_filter=scroll_filter,
            with_vectors=False,
            with_payload=False,
            limit=256,
            offset=offset,
        )
        ids = [p.id for p in batch]
        if ids:
            client.delete(collection_name=collection, points_selector=qmodels.PointIdsList(points=ids))
            deleted += len(ids)
        if offset is None or not batch:
            break
    return deleted


def enforce_qdrant_limits() -> dict[str, dict[str, int]] | None:
    client = get_qdrant_client()
    if client is None:
        logger.info("Qdrant not configured; skip vector cleanup.")
        return None

    summary: dict[str, dict[str, int]] = {}
    for collection in QDRANT_COLLECTIONS:
        try:
            info = client.get_collection(collection)
        except Exception:  # noqa: BLE001
            logger.info("Qdrant collection %s missing, skip", collection)
            continue

        deleted_user, deleted_dialog = trim_collection_limits(client, collection)
        deleted_ttl = trim_collection_ttl(client, collection)
        summary[collection] = {
            "deleted_user": deleted_user,
            "deleted_dialog": deleted_dialog,
            "deleted_ttl": deleted_ttl,
            "vectors": info.points_count if hasattr(info, "points_count") else 0,
        }
        if any(summary[collection].values()):
            logger.info(
                "Qdrant cleanup %s: user %s, dialog %s, ttl %s, total %s",
                collection,
                deleted_user,
                deleted_dialog,
                deleted_ttl,
                summary[collection]["vectors"],
            )
    return summary
