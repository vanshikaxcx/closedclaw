"""
ArthSetu PayBot — Shopping Agent
Merchant search and order preparation tools.
Operates within the scope enforcer's constraints.
"""

import json
import uuid

from backend.db import get_connection, get_all_merchants, get_merchant_products, get_merchant
from backend.audit import append_audit


def search_merchants(items: list[str], token_id: str | None = None) -> dict:
    """
    Find merchants whose catalog matches the requested items.
    Returns merchants with their matching products and prices.
    """
    conn = get_connection()
    all_merchants = get_all_merchants(conn)
    results = []

    for merchant in all_merchants:
        products = get_merchant_products(conn, merchant["merchant_id"])
        matching = []

        for item_name in items:
            item_lower = item_name.lower()
            for product in products:
                prod_name_lower = product["name"].lower()
                # Fuzzy match: check if item keyword appears in product name
                if (item_lower in prod_name_lower or
                    prod_name_lower in item_lower or
                    any(word in prod_name_lower for word in item_lower.split())):
                    matching.append({
                        "product_id": product["product_id"],
                        "name": product["name"],
                        "price": product["price"],
                        "unit": product["unit"],
                        "hsn_code": product["hsn_code"],
                        "gst_rate": product["gst_rate"],
                        "stock_qty": product["stock_qty"],
                        "matched_query": item_name,
                    })

        if matching:
            results.append({
                "merchant_id": merchant["merchant_id"],
                "name": merchant["name"],
                "category": merchant["category"],
                "location": merchant["location"],
                "matching_products": matching,
            })

    conn.close()

    # Audit the search
    if token_id:
        append_audit(
            token_id=token_id,
            action_type="MERCHANT_SEARCHED",
            actor="shopping_agent",
            outcome="success",
            payload={"items_searched": items, "merchants_found": len(results)},
        )

    return {
        "merchants": results,
        "total_found": len(results),
        "items_searched": items,
    }


def prepare_order(
    merchant_id: str,
    items: list[dict],
    token_id: str | None = None,
) -> dict:
    """
    Build a line-item order from a merchant's catalog.
    items: [{"name": "atta", "qty": 2}, ...]
    Returns order with line items, total, and merchant signature.
    """
    conn = get_connection()
    merchant = get_merchant(conn, merchant_id)

    if not merchant:
        conn.close()
        return {"error": f"Merchant {merchant_id} not found"}

    products = get_merchant_products(conn, merchant_id)
    conn.close()

    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    line_items = []
    total = 0.0
    category = merchant["category"]

    for item_request in items:
        req_name = item_request.get("name", "").lower()
        req_qty = item_request.get("qty", 1)

        # Find matching product in catalog
        matched_product = None
        for product in products:
            prod_lower = product["name"].lower()
            if (req_name in prod_lower or
                prod_lower in req_name or
                any(word in prod_lower for word in req_name.split())):
                matched_product = product
                break

        if matched_product:
            item_total = matched_product["price"] * req_qty
            total += item_total
            line_items.append({
                "product_id": matched_product["product_id"],
                "name": matched_product["name"],
                "unit_price": matched_product["price"],
                "qty": req_qty,
                "total": item_total,
                "hsn_code": matched_product["hsn_code"],
                "gst_rate": matched_product["gst_rate"],
            })
        else:
            line_items.append({
                "name": item_request.get("name", "Unknown"),
                "error": "Product not found in catalog",
                "qty": req_qty,
            })

    order = {
        "order_id": order_id,
        "merchant_id": merchant_id,
        "merchant_name": merchant["name"],
        "category": category,
        "line_items": line_items,
        "total_inr": round(total, 2),
        "merchant_signature": f"sig_{uuid.uuid4().hex[:8]}",  # Simulated
    }

    # Audit the order preparation
    if token_id:
        append_audit(
            token_id=token_id,
            action_type="ORDER_PREPARED",
            actor="shopping_agent",
            entity_id=order_id,
            amount=total,
            category=category,
            merchant_id=merchant_id,
            outcome="success",
            payload={"line_items": len(line_items), "total": total},
        )

    return order
