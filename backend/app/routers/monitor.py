from fastapi import APIRouter
from app.monitor.network_watch import get_monitor_status

router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/connections")
async def get_connections_status():
    """
    Returns real-time verification of local loopback connections vs zero external network calls.
    Used for live hackathon proof of air-gapped sovereignty.
    """
    return get_monitor_status()
