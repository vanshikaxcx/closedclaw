"""
Socket.IO Manager for Real-Time Updates
Handles WebSocket connections and event broadcasting
"""
import socketio
from typing import Dict, Any
from app.munim.config import get_munim_config

config = get_munim_config()

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=config.SOCKETIO_CORS_ORIGINS + ["*"],  # Permissive for development
    logger=False,
    engineio_logger=False
)


class SocketIOManager:
    """Manages Socket.IO connections and events"""
    
    def __init__(self):
        self.sio = sio
        self._setup_events()
    
    def _setup_events(self):
        """Setup Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ):
            print(f"🔌 Client connected: {sid}")
        
        @self.sio.event
        async def disconnect(sid):
            print(f"🔌 Client disconnected: {sid}")
        
        @self.sio.event
        async def join_merchant(sid, data):
            """Subscribe to a merchant's real-time updates"""
            merchant_id = data.get("merchant_id")
            if merchant_id:
                await self.sio.enter_room(sid, f"merchant_{merchant_id}")
                print(f"📡 {sid} joined room: merchant_{merchant_id}")
                await self.sio.emit("joined", {"merchant_id": merchant_id}, room=sid)
        
        @self.sio.event
        async def leave_merchant(sid, data):
            """Unsubscribe from a merchant's updates"""
            merchant_id = data.get("merchant_id")
            if merchant_id:
                await self.sio.enter_room(sid, f"merchant_{merchant_id}")
                print(f"📡 {sid} left room: merchant_{merchant_id}")
    
    async def emit_transaction_update(self, merchant_id: str, transaction: Dict[str, Any]):
        """Emit transaction update to merchant's room"""
        room = f"merchant_{merchant_id}"
        await self.sio.emit("transaction_update", transaction, room=room)
        print(f"📤 Emitted transaction update to {room}")
    
    async def emit_dashboard_update(self, merchant_id: str, dashboard_data: Dict[str, Any]):
        """Emit dashboard update to merchant's room"""
        room = f"merchant_{merchant_id}"
        await self.sio.emit("dashboard_update", dashboard_data, room=room)
        print(f"📤 Emitted dashboard update to {room}")
    
    async def emit_udhari_update(self, merchant_id: str, udhari_data: Dict[str, Any]):
        """Emit udhari update to merchant's room"""
        room = f"merchant_{merchant_id}"
        await self.sio.emit("udhari_update", udhari_data, room=room)
        print(f"📤 Emitted udhari update to {room}")
    
    def get_asgi_app(self, fastapi_app):
        """Get Socket.IO ASGI app wrapped around FastAPI"""
        return socketio.ASGIApp(self.sio, other_asgi_app=fastapi_app)


# Singleton instance
_socketio_manager = None

def get_socketio_manager() -> SocketIOManager:
    """Get Socket.IO manager singleton"""
    global _socketio_manager
    if _socketio_manager is None:
        _socketio_manager = SocketIOManager()
    return _socketio_manager
