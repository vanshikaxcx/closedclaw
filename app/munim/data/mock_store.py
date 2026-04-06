"""
Mock data storage for Arthsetu Merchant Help features
Uses in-memory storage instead of database migrations
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List
from collections import defaultdict
import json
import os

# In-memory storage
MOCK_DATA: Dict[str, Any] = {
    "voice_commands": [],
    "transactions": [],
    "udhari": [],
    "payscore_history": [],
    "forecasts": [],
    "gst_classifications": [],
    "customers": [],
    "schemes": [],
    "recurring_payments": [],
    "whatsapp_messages": [],
    "agent_logs": [],
    "collection_history": [],
}

# File path for persistence
MOCK_DATA_FILE = "closedclaw/backend/app/munim/data/mock_data.json"


def load_mock_data():
    """Load mock data from file if exists"""
    global MOCK_DATA
    if os.path.exists(MOCK_DATA_FILE):
        try:
            with open(MOCK_DATA_FILE, 'r') as f:
                MOCK_DATA = json.load(f)
        except Exception as e:
            print(f"Error loading mock data: {e}")


def save_mock_data():
    """Save mock data to file"""
    try:
        os.makedirs(os.path.dirname(MOCK_DATA_FILE), exist_ok=True)
        with open(MOCK_DATA_FILE, 'w') as f:
            json.dump(MOCK_DATA, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving mock data: {e}")


def get_collection(collection_name: str) -> List[Dict[str, Any]]:
    """Get all items from a collection"""
    return MOCK_DATA.get(collection_name, [])


def add_to_collection(collection_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Add item to collection"""
    if collection_name not in MOCK_DATA:
        MOCK_DATA[collection_name] = []
    
    # Add timestamp if not present
    if "created_at" not in item:
        item["created_at"] = datetime.utcnow().isoformat()
    
    MOCK_DATA[collection_name].append(item)
    save_mock_data()
    return item


def update_in_collection(collection_name: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update item in collection"""
    collection = MOCK_DATA.get(collection_name, [])
    for item in collection:
        if item.get("id") == item_id:
            item.update(updates)
            item["updated_at"] = datetime.utcnow().isoformat()
            save_mock_data()
            return item
    return None


def delete_from_collection(collection_name: str, item_id: str) -> bool:
    """Delete item from collection"""
    collection = MOCK_DATA.get(collection_name, [])
    for i, item in enumerate(collection):
        if item.get("id") == item_id:
            collection.pop(i)
            save_mock_data()
            return True
    return False


def filter_collection(collection_name: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter collection by criteria"""
    collection = MOCK_DATA.get(collection_name, [])
    results = []
    
    for item in collection:
        match = True
        for key, value in filters.items():
            if item.get(key) != value:
                match = False
                break
        if match:
            results.append(item)
    
    return results


def clear_collection(collection_name: str):
    """Clear all items from collection"""
    MOCK_DATA[collection_name] = []
    save_mock_data()


def seed_demo_data(merchant_id: str = "demo_merchant"):
    """Seed demo data for testing"""
    # Clear existing data
    for key in MOCK_DATA:
        MOCK_DATA[key] = []
    
    # Seed transactions
    base_date = datetime.utcnow() - timedelta(days=30)
    for i in range(50):
        add_to_collection("transactions", {
            "id": f"txn_{i}",
            "merchant_id": merchant_id,
            "type": "income" if i % 3 != 0 else "expense",
            "amount": 1000 + (i * 100),
            "party_name": f"Customer {i % 10}",
            "payment_mode": "upi" if i % 2 == 0 else "cash",
            "description": f"Transaction {i}",
            "created_at": (base_date + timedelta(days=i % 30)).isoformat()
        })
    
    # Seed udhari
    for i in range(5):
        add_to_collection("udhari", {
            "id": f"udhari_{i}",
            "merchant_id": merchant_id,
            "debtor_name": f"Debtor {i}",
            "debtor_phone": f"+91900000000{i}",
            "amount": 5000 + (i * 1000),
            "due_date": (datetime.utcnow() + timedelta(days=i * 7)).isoformat(),
            "risk_score": 30 + (i * 15),
            "status": "pending",
            "reminders_sent": 0
        })
    
    # Seed customers
    for i in range(10):
        add_to_collection("customers", {
            "id": f"customer_{i}",
            "merchant_id": merchant_id,
            "name": f"Customer {i}",
            "phone": f"+91900000010{i}",
            "total_transactions": 5 + i,
            "total_value": 10000 + (i * 2000),
            "last_transaction": (datetime.utcnow() - timedelta(days=i)).isoformat(),
            "segment": "champion" if i < 3 else "loyal" if i < 6 else "promising"
        })
    
    print(f"✅ Seeded demo data for merchant: {merchant_id}")


# Load data on module import
load_mock_data()
