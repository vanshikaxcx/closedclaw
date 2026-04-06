"""
Run the FastAPI app with Socket.IO support
This wraps the main FastAPI app with Socket.IO ASGI app
"""
import uvicorn
from app.main import app
from app.munim.services.socketio_manager import get_socketio_manager

# Get Socket.IO manager
socketio_manager = get_socketio_manager()

# Wrap FastAPI app with Socket.IO
socket_app = socketio_manager.get_asgi_app(app)

if __name__ == "__main__":
    uvicorn.run(
        "run_with_socketio:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
