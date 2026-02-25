from fastapi import APIRouter
from app.core.config import settings
from app.services.lan import local_ips

router = APIRouter(prefix='/api', tags=['network'])


@router.get('/network/addresses')
def addresses():
    return {'ips': local_ips(), 'port': settings.growora_bind_port, 'mode': settings.growora_network_mode}
