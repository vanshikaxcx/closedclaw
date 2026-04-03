"""
Integration tests for Appwrite database connectivity and CRUD operations.

These tests verify:
  - Appwrite credentials are configured and the client can connect
  - All required collections can be read/written
  - The seed data layer works correctly (upsert / get / list / delete)
  - The full startup sequence (init_firestore + ensure_seed_data) completes

Run with:
    cd backend
    python -m pytest tests/test_db_integration.py -v --timeout=120

The test file is deleted automatically by CI after a green run.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make sure the backend package is importable regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load .env before importing any app modules
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    """Initialise and return a live Appwrite database client."""
    from app.database import init_firestore
    client = init_firestore()
    assert client is not None, "init_firestore() returned None"
    return client


# ---------------------------------------------------------------------------
# 1. Credential check
# ---------------------------------------------------------------------------

class TestCredentials:
    def test_appwrite_endpoint_set(self):
        endpoint = os.getenv("APPWRITE_ENDPOINT", "")
        assert endpoint, "APPWRITE_ENDPOINT is not set in .env"
        assert endpoint.startswith("https://"), f"APPWRITE_ENDPOINT looks wrong: {endpoint}"

    def test_appwrite_project_id_set(self):
        assert os.getenv("APPWRITE_PROJECT_ID", ""), "APPWRITE_PROJECT_ID is missing"

    def test_appwrite_api_key_set(self):
        key = os.getenv("APPWRITE_API_KEY", "")
        assert key, "APPWRITE_API_KEY is missing"

    def test_database_id_set(self):
        db_id = os.getenv("DATABASE_ID", "") or os.getenv("APPWRITE_DATABASE_ID", "")
        assert db_id, "DATABASE_ID (or APPWRITE_DATABASE_ID) is missing"


# ---------------------------------------------------------------------------
# 2. Connection & collection bootstrap
# ---------------------------------------------------------------------------

class TestConnection:
    def test_client_initialises(self, db):
        """init_firestore() should return an AppwriteFirestoreCompat instance."""
        from app.database import AppwriteFirestoreCompat
        assert isinstance(db, AppwriteFirestoreCompat)

    def test_all_collections_accessible(self, db):
        """Every collection in ALL_COLLECTIONS must be reachable (no exception)."""
        from app.database import ALL_COLLECTIONS
        for name in ALL_COLLECTIONS:
            ref = db.collection(name)
            assert ref is not None, f"collection({name!r}) returned None"


# ---------------------------------------------------------------------------
# 3. CRUD round-trip
# ---------------------------------------------------------------------------

_TEST_COLLECTION = "audit_log"          # always exists; safe to write a test doc
_TEST_DOC_ID     = "_pytest_integration_db_probe_"


class TestCRUD:
    def test_upsert_and_get(self, db):
        """Write a document, read it back, and verify the round-trip."""
        from app.database import upsert_document, get_document

        payload = {
            "probe": True,
            "message": "integration-test",
            "value": 42,
        }
        upsert_document(db, _TEST_COLLECTION, _TEST_DOC_ID, payload, merge=False)

        fetched = get_document(db, _TEST_COLLECTION, _TEST_DOC_ID)
        assert fetched is not None, "get_document returned None after upsert"
        assert fetched.get("probe") is True
        assert fetched.get("message") == "integration-test"
        assert fetched.get("value") == 42

    def test_list_includes_probe_doc(self, db):
        """list_documents should surface the doc we just wrote."""
        from app.database import list_documents

        rows = list_documents(db, _TEST_COLLECTION)
        assert isinstance(rows, list), "list_documents must return a list"
        ids = [str(r.get("id", "")) for r in rows]
        assert _TEST_DOC_ID in ids, (
            f"Probe doc {_TEST_DOC_ID!r} not found in list_documents result. "
            f"First 5 ids: {ids[:5]}"
        )

    def test_delete_probe_doc(self, db):
        """Deleting the probe doc should make get_document return None."""
        from app.database import delete_document, get_document

        delete_document(db, _TEST_COLLECTION, _TEST_DOC_ID)
        after = get_document(db, _TEST_COLLECTION, _TEST_DOC_ID)
        assert after is None, "get_document should return None after delete"


# ---------------------------------------------------------------------------
# 4. Merchant collection
# ---------------------------------------------------------------------------

class TestMerchants:
    def test_merchant_collection_listable(self, db):
        from app.database import list_documents, COLL_MERCHANTS
        rows = list_documents(db, COLL_MERCHANTS)
        assert isinstance(rows, list)

    def test_seed_merchant_upsert_and_fetch(self, db):
        """Write a minimal merchant doc and verify it can be fetched."""
        from app.database import upsert_document, get_document, delete_document, COLL_MERCHANTS

        test_merchant_id = "_pytest_merchant_probe_"
        payload = {
            "merchant_id": test_merchant_id,
            "name": "Test Merchant",
            "business_name": "Test Co.",
            "category": "Test",
            "city": "Delhi",
            "phone": "+91-00000-00000",
            "gstin": "07AAAAA0000A1Z5",
            "kyc_status": "pending",
            "wallet_balance": 0.0,
            "role": "merchant",
            "trust_score": 50,
        }
        upsert_document(db, COLL_MERCHANTS, test_merchant_id, payload, merge=False)
        fetched = get_document(db, COLL_MERCHANTS, test_merchant_id)
        assert fetched is not None
        assert fetched.get("merchant_id") == test_merchant_id
        assert fetched.get("name") == "Test Merchant"

        # clean up
        delete_document(db, COLL_MERCHANTS, test_merchant_id)
        assert get_document(db, COLL_MERCHANTS, test_merchant_id) is None

    def test_merchant_exists_helper(self, db):
        from app.database import merchant_exists, COLL_MERCHANTS
        # Should not raise even when querying a non-existent merchant
        result = merchant_exists(db, "__definitely_does_not_exist_xyz__")
        assert result is False


# ---------------------------------------------------------------------------
# 5. Seed data pipeline
# ---------------------------------------------------------------------------

class TestSeedData:
    def test_ensure_seed_data_runs_without_error(self, db):
        """ensure_seed_data(force=False) must complete without raising."""
        from app.seed import ensure_seed_data
        count = ensure_seed_data(db, force=False)
        assert isinstance(count, int), "ensure_seed_data should return an int (merchant count)"
        assert count >= 1, f"Expected at least 1 merchant after seeding, got {count}"

    def test_seed_merchant_present_after_seed(self, db):
        from app.seed import SEED_MERCHANT_ID
        from app.database import get_document, COLL_MERCHANTS
        doc = get_document(db, COLL_MERCHANTS, SEED_MERCHANT_ID)
        assert doc is not None, f"Seed merchant {SEED_MERCHANT_ID!r} not found after ensure_seed_data"
        assert doc.get("merchant_id") == SEED_MERCHANT_ID

    def test_gst_draft_present_after_seed(self, db):
        from app.seed import SEED_MERCHANT_ID
        from app.database import get_document, COLL_GST_DRAFTS
        doc = get_document(db, COLL_GST_DRAFTS, SEED_MERCHANT_ID)
        assert doc is not None, "GST draft not found after seeding"
        assert "transactions" in doc, "GST draft missing 'transactions' key"
        assert isinstance(doc["transactions"], list), "'transactions' should be a list"
        assert len(doc["transactions"]) > 0, "GST draft has no transactions"

    def test_transactions_seeded(self, db):
        from app.seed import SEED_MERCHANT_ID
        from app.database import list_documents, COLL_TRANSACTIONS
        rows = list_documents(
            db,
            COLL_TRANSACTIONS,
            filters=[("merchant_id", "==", SEED_MERCHANT_ID)],
            limit=5,
        )
        assert isinstance(rows, list)
        assert len(rows) > 0, "No transactions found for seed merchant"


# ---------------------------------------------------------------------------
# 6. GST draft collection read/write
# ---------------------------------------------------------------------------

class TestGSTDrafts:
    def test_gst_draft_write_and_read(self, db):
        from app.database import upsert_document, get_document, delete_document, COLL_GST_DRAFTS
        from app.database import utc_now_iso

        doc_id = "_pytest_gst_draft_probe_"
        payload = {
            "merchant_id": doc_id,
            "quarter": "Q1",
            "year": 2026,
            "transactions": [
                {
                    "tx_id": "PROBE-001",
                    "amount": 1000.0,
                    "gst_rate": 0.18,
                    "review_flag": False,
                }
            ],
            "summary": {"total_taxable": 1000.0, "net_liability": 180.0},
            "generated_at": utc_now_iso(),
        }
        upsert_document(db, COLL_GST_DRAFTS, doc_id, payload, merge=False)
        fetched = get_document(db, COLL_GST_DRAFTS, doc_id)
        assert fetched is not None
        assert fetched.get("quarter") == "Q1"
        txns = fetched.get("transactions", [])
        assert len(txns) == 1
        assert txns[0]["tx_id"] == "PROBE-001"

        delete_document(db, COLL_GST_DRAFTS, doc_id)
        assert get_document(db, COLL_GST_DRAFTS, doc_id) is None


# ---------------------------------------------------------------------------
# 7. FastAPI app startup smoke test
# ---------------------------------------------------------------------------

class TestAppStartup:
    def test_fastapi_app_imports_and_has_routes(self):
        """The FastAPI app must be importable and have /api/health registered."""
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("/health" in p for p in routes), (
            f"Expected /api/health in routes. Got: {routes}"
        )

    def test_health_endpoint_via_test_client(self):
        """GET /api/health must return 200 via in-process TestClient."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/health")
        assert resp.status_code == 200, (
            f"/api/health returned {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert data.get("status") in ("ok", "healthy", "degraded"), (
            f"Unexpected health status: {data}"
        )
