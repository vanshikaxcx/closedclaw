"""
Dashboard Router
Handles real-time dashboard data and P&L updates
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from app.munim.data.mock_store import get_collection, add_to_collection, filter_collection
from app.munim.services.socketio_manager import get_socketio_manager

router = APIRouter()


class TransactionCreate(BaseModel):
    """Create transaction request"""
    merchant_id: str = "demo_merchant"
    type: str  # income, expense, udhari
    amount: float
    party_name: str = None
    payment_mode: str = "cash"  # cash, upi, card
    description: str = None


class DashboardSummary(BaseModel):
    """Dashboard summary response"""
    merchant_id: str
    total_income: float
    total_expense: float
    total_udhari: float
    net_profit: float
    payment_mode_breakdown: Dict[str, float]
    transaction_count: int
    period: str


@router.get("/api/munim/dashboard/summary")
async def get_dashboard_summary(
    merchant_id: str = "demo_merchant",
    period: str = "today"  # today, week, month, all
):
    """
    Get dashboard summary with P&L data
    """
    try:
        # Get all transactions for merchant
        all_transactions = filter_collection("transactions", {"merchant_id": merchant_id})
        
        # Filter by period
        now = datetime.utcnow()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = datetime.min
        
        filtered_transactions = [
            txn for txn in all_transactions
            if datetime.fromisoformat(txn.get("created_at", "")) >= start_date
        ]
        
        # Calculate totals
        total_income = sum(
            txn["amount"] for txn in filtered_transactions 
            if txn.get("type") == "income"
        )
        total_expense = sum(
            txn["amount"] for txn in filtered_transactions 
            if txn.get("type") == "expense"
        )
        total_udhari = sum(
            txn["amount"] for txn in filtered_transactions 
            if txn.get("type") == "udhari"
        )
        
        # Payment mode breakdown
        payment_breakdown = defaultdict(float)
        for txn in filtered_transactions:
            mode = txn.get("payment_mode", "cash")
            payment_breakdown[mode] += txn["amount"]
        
        return DashboardSummary(
            merchant_id=merchant_id,
            total_income=round(total_income, 2),
            total_expense=round(total_expense, 2),
            total_udhari=round(total_udhari, 2),
            net_profit=round(total_income - total_expense, 2),
            payment_mode_breakdown=dict(payment_breakdown),
            transaction_count=len(filtered_transactions),
            period=period
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard: {str(e)}")


@router.post("/api/munim/dashboard/transaction")
async def create_transaction(transaction: TransactionCreate):
    """
    Create a new transaction and emit real-time update
    """
    try:
        import uuid
        
        # Create transaction record
        txn_record = {
            "id": str(uuid.uuid4()),
            "merchant_id": transaction.merchant_id,
            "type": transaction.type,
            "amount": transaction.amount,
            "party_name": transaction.party_name,
            "payment_mode": transaction.payment_mode,
            "description": transaction.description,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save to mock store
        add_to_collection("transactions", txn_record)
        
        # Get updated dashboard summary
        summary = await get_dashboard_summary(transaction.merchant_id, "today")
        
        # Emit real-time update via Socket.IO
        socketio_manager = get_socketio_manager()
        await socketio_manager.emit_transaction_update(
            transaction.merchant_id,
            {
                "transaction": txn_record,
                "summary": summary.dict()
            }
        )
        
        return {
            "success": True,
            "transaction": txn_record,
            "summary": summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {str(e)}")


@router.get("/api/munim/dashboard/transactions")
async def get_transactions(
    merchant_id: str = "demo_merchant",
    limit: int = 50,
    type: str = None  # Filter by type: income, expense, udhari
):
    """
    Get transaction list for merchant
    """
    try:
        # Get all transactions for merchant
        transactions = filter_collection("transactions", {"merchant_id": merchant_id})
        
        # Filter by type if specified
        if type:
            transactions = [txn for txn in transactions if txn.get("type") == type]
        
        # Sort by date (most recent first)
        transactions.sort(
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        
        return {
            "merchant_id": merchant_id,
            "total": len(transactions),
            "transactions": transactions[:limit]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transactions: {str(e)}")


@router.get("/api/munim/dashboard/chart-data")
async def get_chart_data(
    merchant_id: str = "demo_merchant",
    period: str = "week"  # week, month
):
    """
    Get chart data for dashboard visualizations
    """
    try:
        # Get all transactions for merchant
        all_transactions = filter_collection("transactions", {"merchant_id": merchant_id})
        
        # Determine date range
        now = datetime.utcnow()
        if period == "week":
            days = 7
        elif period == "month":
            days = 30
        else:
            days = 7
        
        # Group by date
        daily_data = defaultdict(lambda: {"income": 0, "expense": 0, "udhari": 0})
        
        for txn in all_transactions:
            txn_date = datetime.fromisoformat(txn.get("created_at", "")).date()
            date_str = txn_date.isoformat()
            txn_type = txn.get("type", "income")
            amount = txn.get("amount", 0)
            
            daily_data[date_str][txn_type] += amount
        
        # Generate chart data for last N days
        chart_data = []
        for i in range(days):
            date = (now - timedelta(days=days - i - 1)).date()
            date_str = date.isoformat()
            data = daily_data.get(date_str, {"income": 0, "expense": 0, "udhari": 0})
            
            chart_data.append({
                "date": date_str,
                "income": round(data["income"], 2),
                "expense": round(data["expense"], 2),
                "udhari": round(data["udhari"], 2),
                "profit": round(data["income"] - data["expense"], 2)
            })
        
        return {
            "merchant_id": merchant_id,
            "period": period,
            "data": chart_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chart data: {str(e)}")
