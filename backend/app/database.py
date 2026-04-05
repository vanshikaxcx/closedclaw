from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import threading
import time
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from appwrite.client import Client as AppwriteClient
from appwrite.exception import AppwriteException
from appwrite.query import Query
from appwrite.services.databases import Databases
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)

COLL_MERCHANTS = "merchants"
COLL_TRANSACTIONS = "transactions"
COLL_INVOICES = "invoices"
COLL_CREDIT_OFFERS = "credit_offers"
COLL_FINANCING_LEDGER = "financing_ledger"
COLL_TRUSTSCORE_HISTORY = "trustscore_history"
COLL_AUDIT_LOG = "audit_log"
COLL_NOTIFICATIONS = "notifications"
COLL_WHATSAPP_LOG = "whatsapp_log"
COLL_GST_DRAFTS = "gst_drafts"
COLL_DEMO_STATE = "demo_state"
COLL_PENDING_TRANSFERS = "pending_transfers"

ALL_COLLECTIONS = [
    COLL_MERCHANTS,
    COLL_TRANSACTIONS,
    COLL_INVOICES,
    COLL_CREDIT_OFFERS,
    COLL_FINANCING_LEDGER,
    COLL_TRUSTSCORE_HISTORY,
    COLL_AUDIT_LOG,
    COLL_NOTIFICATIONS,
    COLL_WHATSAPP_LOG,
    COLL_GST_DRAFTS,
    COLL_DEMO_STATE,
    COLL_PENDING_TRANSFERS,
]

# Firestore-like appwrite compatibility constants.
_APPWRITE_ATTR_DOC_ID = "doc_id"
_APPWRITE_ATTR_PAYLOAD = "payload"
_APPWRITE_ATTR_UPDATED_AT = "updated_at"
_APPWRITE_PAYLOAD_SIZE = 65535
_APPWRITE_PAGE_SIZE = 100
_APPWRITE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,36}$")

_firestore_client: AppwriteFirestoreCompat | None = None
_firestore_lock = threading.Lock()
_cache: dict[str, Any] = {"trustscore": {}}


# ---------------------------------------------------------------------------
# Appwrite SDK v9+ compatibility helpers
# ---------------------------------------------------------------------------
# Appwrite Python SDK ≥ 1.8 / v9 returns typed pydantic models instead of
# plain dicts for all API responses. These helpers abstract over both shapes
# so the rest of the code base does not need to change.

def _sdk_unwrap_list(response: Any, key: str) -> list[Any]:
    """Extract a list field from either a plain dict or an Appwrite pydantic model."""
    if isinstance(response, dict):
        return response.get(key, []) or []
    return getattr(response, key, None) or []


def _sdk_attr_field(attr: Any, field: str, default: str = "") -> str:
    """Read a string field from either a dict attribute or an SDK attribute model."""
    if isinstance(attr, dict):
        return str(attr.get(field, default) or default)
    return str(getattr(attr, field, None) or default)


def _sdk_doc_to_dict(doc: Any) -> dict[str, Any]:
    """Convert an Appwrite SDK Document model (or plain dict) to a plain Python dict.

    Custom collection attributes land in ``model_extra`` (pydantic v2) which we
    must merge with the standard system fields so downstream code can call
    ``.get(key)`` as usual.
    """
    if isinstance(doc, dict):
        return doc
    base: dict[str, Any] = {}
    # Standard SDK system fields
    for _f in ("id", "collection_id", "database_id", "created_at", "updated_at", "permissions"):
        _v = getattr(doc, _f, None)
        if _v is not None:
            base[_f] = _v
    # Keep $id alias that older code may rely on
    doc_id_val = getattr(doc, "id", None) or base.get("id")
    if doc_id_val:
        base["$id"] = doc_id_val
    # pydantic v2: extra/custom attributes live in model_extra
    try:
        extra = getattr(doc, "model_extra", None) or {}
        if isinstance(extra, dict):
            base.update(extra)
    except Exception:
        pass
    # Last-resort fallback: model_dump() captures everything
    if not any(k in base for k in ("doc_id", "payload", "$id")):
        try:
            dumped = doc.model_dump() if hasattr(doc, "model_dump") else {}
            if isinstance(dumped, dict):
                base.update({k: v for k, v in dumped.items() if k not in base})
        except Exception:
            pass
    return base


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def demo_mode_enabled() -> bool:
    # Demo-only fixtures and seed data should be explicitly enabled.
    return _env_flag("ARTHSETU_DEMO_MODE", default=False)


def demo_seed_on_startup_enabled() -> bool:
    return demo_mode_enabled() and _env_flag("ARTHSETU_DEMO_SEED_ON_STARTUP", default=True)


def demo_reset_enabled() -> bool:
    return demo_mode_enabled() and _env_flag("ARTHSETU_ENABLE_DEMO_RESET", default=False)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _to_appwrite_document_id(doc_id: str) -> str:
    candidate = str(doc_id or "").strip()
    if _APPWRITE_ID_PATTERN.fullmatch(candidate):
        return candidate
    digest = hashlib.sha1(candidate.encode("utf-8")).hexdigest()
    return f"h{digest[:35]}"


def _encode_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    encoded = base64.b64encode(compressed).decode("ascii")
    if len(encoded) > _APPWRITE_PAYLOAD_SIZE:
        raise ValueError("serialized payload exceeds configured Appwrite payload size")
    return encoded


def _decode_payload(encoded_payload: Any) -> dict[str, Any]:
    if not isinstance(encoded_payload, str) or not encoded_payload:
        return {}

    try:
        packed = base64.b64decode(encoded_payload.encode("ascii"))
        raw = zlib.decompress(packed).decode("utf-8")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Backward compatibility with plain-json payload strings.
    try:
        parsed = json.loads(encoded_payload)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {}


def _is_not_found(exc: AppwriteException) -> bool:
    code = getattr(exc, "code", None)
    return code == 404


class AppwriteDocumentSnapshot:
    def __init__(self, db: AppwriteFirestoreCompat, collection_name: str, doc_id: str, payload: dict[str, Any], exists: bool):
        self._db = db
        self._collection_name = collection_name
        self.id = doc_id
        self._payload = dict(payload)
        self.exists = bool(exists)

    @property
    def reference(self) -> AppwriteDocumentReference:
        return AppwriteDocumentReference(self._db, self._collection_name, self.id)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._payload)


class AppwriteDocumentReference:
    def __init__(self, db: AppwriteFirestoreCompat, collection_name: str, doc_id: str):
        self._db = db
        self._collection_name = collection_name
        self._doc_id = str(doc_id)

    def get(self, timeout: float | None = None) -> AppwriteDocumentSnapshot:
        _ = timeout
        payload, exists = self._db._get_document_payload(self._collection_name, self._doc_id)
        return AppwriteDocumentSnapshot(self._db, self._collection_name, self._doc_id, payload, exists)

    def set(
        self,
        payload: dict[str, Any],
        merge: bool = True,
        retry: Any | None = None,
        timeout: float | None = None,
    ) -> None:
        _ = retry
        _ = timeout

        if merge:
            existing, exists = self._db._get_document_payload(self._collection_name, self._doc_id)
            next_payload = dict(existing if exists else {})
            next_payload.update(payload)
        else:
            next_payload = dict(payload)

        self._db._write_document_payload(self._collection_name, self._doc_id, next_payload)

    def delete(self, retry: Any | None = None, timeout: float | None = None) -> None:
        _ = retry
        _ = timeout
        self._db._delete_document(self._collection_name, self._doc_id)


class AppwriteQueryReference:
    def __init__(self, collection_ref: AppwriteCollectionReference):
        self._collection_ref = collection_ref
        self._filters: list[tuple[str, str, Any]] = []
        self._order_by: str | None = None
        self._descending = False
        self._limit: int | None = None

    def where(self, filter: Any = None) -> AppwriteQueryReference:
        if filter is None:
            return self

        field_name = getattr(filter, "field_path", None) or getattr(filter, "field", None)
        op = getattr(filter, "op_string", None) or getattr(filter, "op", None)
        value = getattr(filter, "value", None)
        if field_name is None or op is None:
            raise ValueError("Unsupported query filter object")
        self._filters.append((str(field_name), str(op), value))
        return self

    def order_by(self, field_name: str, direction: Any = None) -> AppwriteQueryReference:
        self._order_by = field_name
        direction_raw = str(direction).lower() if direction is not None else ""
        self._descending = "desc" in direction_raw
        return self

    def limit(self, value: int) -> AppwriteQueryReference:
        self._limit = value
        return self

    def stream(self) -> Iterator[AppwriteDocumentSnapshot]:
        rows = [doc_to_dict(snapshot) for snapshot in self._collection_ref.stream()]
        rows = _apply_filters(rows, self._filters)

        if self._order_by:
            rows = _sort_rows(rows, self._order_by, self._descending)

        if self._limit is not None:
            rows = rows[: self._limit]

        for row in rows:
            doc_id = str(row.get("id") or row.get("doc_id") or "")
            yield AppwriteDocumentSnapshot(self._collection_ref._db, self._collection_ref._name, doc_id, row, True)


class AppwriteCollectionReference:
    def __init__(self, db: AppwriteFirestoreCompat, collection_name: str):
        self._db = db
        self._name = collection_name

    def document(self, doc_id: str) -> AppwriteDocumentReference:
        return AppwriteDocumentReference(self._db, self._name, doc_id)

    def limit(self, value: int) -> AppwriteQueryReference:
        return AppwriteQueryReference(self).limit(value)

    def stream(self) -> Iterator[AppwriteDocumentSnapshot]:
        raw_documents = self._db._list_raw_documents(self._name)
        for raw_document in raw_documents:
            doc_id = str(raw_document.get(_APPWRITE_ATTR_DOC_ID) or raw_document.get("$id") or "")
            payload = _decode_payload(raw_document.get(_APPWRITE_ATTR_PAYLOAD))
            yield AppwriteDocumentSnapshot(self._db, self._name, doc_id, payload, True)


class AppwriteBatch:
    def __init__(self):
        self._ops: list[tuple[str, AppwriteDocumentReference, dict[str, Any] | None, bool]] = []

    def set(self, reference: AppwriteDocumentReference, payload: dict[str, Any], merge: bool = True) -> None:
        self._ops.append(("set", reference, dict(payload), merge))

    def delete(self, reference: AppwriteDocumentReference) -> None:
        self._ops.append(("delete", reference, None, False))

    def commit(self, retry: Any | None = None, timeout: float | None = None) -> None:
        _ = retry
        _ = timeout
        for op, reference, payload, merge in self._ops:
            if op == "set" and payload is not None:
                reference.set(payload, merge=merge)
            elif op == "delete":
                reference.delete()
        self._ops.clear()


class AppwriteFirestoreCompat:
    def __init__(self, service: Databases, database_id: str):
        self._service = service
        self._database_id = database_id
        self._bootstrap_lock = threading.Lock()
        self._ensured_collections: set[str] = set()

    def collection(self, collection_name: str) -> AppwriteCollectionReference:
        self._ensure_collection(collection_name)
        return AppwriteCollectionReference(self, collection_name)

    def batch(self) -> AppwriteBatch:
        return AppwriteBatch()

    def _ensure_collection(self, collection_name: str) -> None:
        if collection_name in self._ensured_collections:
            return

        with self._bootstrap_lock:
            if collection_name in self._ensured_collections:
                return

            try:
                self._service.get_collection(self._database_id, collection_name)
            except AppwriteException as exc:
                if not _is_not_found(exc):
                    raise
                self._service.create_collection(
                    database_id=self._database_id,
                    collection_id=collection_name,
                    name=collection_name,
                    permissions=[],
                    document_security=False,
                    enabled=True,
                )

            self._ensure_attributes(collection_name)
            self._ensured_collections.add(collection_name)

    def _ensure_attributes(self, collection_name: str) -> None:
        # SDK v9+: list_attributes() returns AttributeList pydantic model, not dict.
        _resp = self._service.list_attributes(self._database_id, collection_name)
        attributes = _sdk_unwrap_list(_resp, "attributes")
        keys = {_sdk_attr_field(attr, "key") for attr in attributes}

        if _APPWRITE_ATTR_DOC_ID not in keys:
            self._service.create_string_attribute(
                database_id=self._database_id,
                collection_id=collection_name,
                key=_APPWRITE_ATTR_DOC_ID,
                size=255,
                required=True,
            )

        if _APPWRITE_ATTR_PAYLOAD not in keys:
            self._service.create_string_attribute(
                database_id=self._database_id,
                collection_id=collection_name,
                key=_APPWRITE_ATTR_PAYLOAD,
                size=_APPWRITE_PAYLOAD_SIZE,
                required=True,
            )

        if _APPWRITE_ATTR_UPDATED_AT not in keys:
            self._service.create_string_attribute(
                database_id=self._database_id,
                collection_id=collection_name,
                key=_APPWRITE_ATTR_UPDATED_AT,
                size=64,
                required=False,
            )

        # Attribute creation is async in Appwrite; wait until fully available.
        for _ in range(30):
            _resp2 = self._service.list_attributes(self._database_id, collection_name)
            attrs = _sdk_unwrap_list(_resp2, "attributes")
            ready = {
                _sdk_attr_field(attr, "key")
                for attr in attrs
                if _sdk_attr_field(attr, "status").lower() in {"available", "enabled"}
            }
            if {
                _APPWRITE_ATTR_DOC_ID,
                _APPWRITE_ATTR_PAYLOAD,
                _APPWRITE_ATTR_UPDATED_AT,
            }.issubset(ready):
                return
            time.sleep(0.2)

    def _list_raw_documents(self, collection_name: str) -> list[dict[str, Any]]:
        self._ensure_collection(collection_name)
        offset = 0
        all_docs: list[dict[str, Any]] = []

        while True:
            query = [Query.limit(_APPWRITE_PAGE_SIZE), Query.offset(offset)]
            response = self._service.list_documents(self._database_id, collection_name, queries=query)
            # SDK v9+: returns DocumentList pydantic model instead of dict.
            page_raw = _sdk_unwrap_list(response, "documents")
            page = [_sdk_doc_to_dict(doc) for doc in page_raw]
            if not page:
                break
            all_docs.extend(page)
            if len(page) < _APPWRITE_PAGE_SIZE:
                break
            offset += len(page)

        return all_docs

    def _get_document_payload(self, collection_name: str, doc_id: str) -> tuple[dict[str, Any], bool]:
        self._ensure_collection(collection_name)
        appwrite_doc_id = _to_appwrite_document_id(doc_id)
        try:
            raw = self._service.get_document(self._database_id, collection_name, appwrite_doc_id)
        except AppwriteException as exc:
            if _is_not_found(exc):
                return {}, False
            raise

        # SDK v9+: get_document() returns a Document pydantic model, not a dict.
        raw_dict = _sdk_doc_to_dict(raw)
        payload = _decode_payload(raw_dict.get(_APPWRITE_ATTR_PAYLOAD))
        return payload, True

    def _write_document_payload(self, collection_name: str, doc_id: str, payload: dict[str, Any]) -> None:
        self._ensure_collection(collection_name)
        appwrite_doc_id = _to_appwrite_document_id(doc_id)
        encoded = _encode_payload(payload)
        data = {
            _APPWRITE_ATTR_DOC_ID: str(doc_id),
            _APPWRITE_ATTR_PAYLOAD: encoded,
            _APPWRITE_ATTR_UPDATED_AT: utc_now_iso(),
        }

        try:
            self._service.update_document(self._database_id, collection_name, appwrite_doc_id, data=data)
        except AppwriteException as exc:
            if not _is_not_found(exc):
                raise
            self._service.create_document(
                database_id=self._database_id,
                collection_id=collection_name,
                document_id=appwrite_doc_id,
                data=data,
            )

    def _delete_document(self, collection_name: str, doc_id: str) -> None:
        self._ensure_collection(collection_name)
        appwrite_doc_id = _to_appwrite_document_id(doc_id)
        try:
            self._service.delete_document(self._database_id, collection_name, appwrite_doc_id)
        except AppwriteException as exc:
            if _is_not_found(exc):
                return
            raise


# Shared DB client alias used across routers and helpers.
DatabaseClient = AppwriteFirestoreCompat


def init_firestore() -> AppwriteFirestoreCompat:
    global _firestore_client

    with _firestore_lock:
        if _firestore_client is not None:
            return _firestore_client

        endpoint = os.getenv("APPWRITE_ENDPOINT", "").strip()
        project_id = os.getenv("APPWRITE_PROJECT_ID", "").strip()
        api_key = os.getenv("APPWRITE_API_KEY", "").strip()
        database_id = os.getenv("DATABASE_ID", "").strip() or os.getenv("APPWRITE_DATABASE_ID", "").strip()

        missing = [
            name
            for name, value in [
                ("APPWRITE_ENDPOINT", endpoint),
                ("APPWRITE_PROJECT_ID", project_id),
                ("APPWRITE_API_KEY", api_key),
                ("DATABASE_ID", database_id),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required Appwrite configuration: {', '.join(missing)}")

        client = AppwriteClient().set_endpoint(endpoint).set_project(project_id).set_key(api_key)
        _firestore_client = AppwriteFirestoreCompat(Databases(client), database_id)
        for collection_name in ALL_COLLECTIONS:
            _firestore_client.collection(collection_name)
        return _firestore_client


def get_db() -> AppwriteFirestoreCompat:
    return init_firestore()


def clear_caches() -> None:
    _cache["trustscore"] = {}


def get_cached_value(namespace: str, key: str) -> Any:
    return _cache.get(namespace, {}).get(key)


def set_cached_value(namespace: str, key: str, value: Any) -> None:
    if namespace not in _cache:
        _cache[namespace] = {}
    _cache[namespace][key] = value


def doc_to_dict(snapshot: Any) -> dict[str, Any]:
    data = snapshot.to_dict() or {}
    if "id" not in data:
        data["id"] = getattr(snapshot, "id", "")
    return data


def _matches_filter(row: dict[str, Any], field_name: str, op: str, value: Any) -> bool:
    field_value = row.get(field_name)

    if op == "==":
        return field_value == value
    if op == "!=":
        return field_value != value
    if op == ">":
        return field_value is not None and field_value > value
    if op == ">=":
        return field_value is not None and field_value >= value
    if op == "<":
        return field_value is not None and field_value < value
    if op == "<=":
        return field_value is not None and field_value <= value
    if op == "in":
        return field_value in value
    if op == "not-in":
        return field_value not in value
    if op == "array_contains":
        return isinstance(field_value, list) and value in field_value
    raise ValueError(f"Unsupported filter op: {op}")


def _apply_filters(rows: list[dict[str, Any]], filters: list[tuple[str, str, Any]]) -> list[dict[str, Any]]:
    filtered = rows
    for field_name, op, value in filters:
        filtered = [row for row in filtered if _matches_filter(row, field_name, op, value)]
    return filtered


def _sort_rows(rows: list[dict[str, Any]], order_by: str, descending: bool) -> list[dict[str, Any]]:
    try:
        return sorted(rows, key=lambda row: row.get(order_by), reverse=descending)
    except TypeError:
        return sorted(rows, key=lambda row: str(row.get(order_by)), reverse=descending)


def get_document(db: AppwriteFirestoreCompat, collection_name: str, doc_id: str) -> dict[str, Any] | None:
    snapshot = db.collection(collection_name).document(doc_id).get()
    if not snapshot.exists:
        return None
    return doc_to_dict(snapshot)


def upsert_document(
    db: AppwriteFirestoreCompat,
    collection_name: str,
    doc_id: str,
    payload: dict[str, Any],
    merge: bool = True,
) -> None:
    db.collection(collection_name).document(doc_id).set(payload, merge=merge)


def delete_document(db: AppwriteFirestoreCompat, collection_name: str, doc_id: str) -> None:
    db.collection(collection_name).document(doc_id).delete()


def list_documents(
    db: AppwriteFirestoreCompat,
    collection_name: str,
    filters: list[tuple[str, str, Any]] | None = None,
    order_by: str | None = None,
    descending: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    rows = [doc_to_dict(doc) for doc in db.collection(collection_name).stream()]
    rows = _apply_filters(rows, filters or [])

    if order_by:
        rows = _sort_rows(rows, order_by, descending)

    if limit is not None:
        rows = rows[:limit]

    return rows


def count_collection(db: AppwriteFirestoreCompat, collection_name: str) -> int:
    return sum(1 for _ in db.collection(collection_name).stream())


def merchant_exists(db: AppwriteFirestoreCompat, merchant_id: str) -> bool:
    snapshot = db.collection(COLL_MERCHANTS).document(merchant_id).get()
    return snapshot.exists


def delete_collection(db: AppwriteFirestoreCompat, collection_name: str, batch_size: int = 400) -> int:
    deleted = 0
    collection_ref = db.collection(collection_name)

    while True:
        docs = list(collection_ref.limit(batch_size).stream())
        if not docs:
            break

        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)
            deleted += 1
        batch.commit()

    return deleted
