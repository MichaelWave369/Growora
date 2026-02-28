from fastapi import APIRouter, Depends

from app.core.auth import require_local_admin
from app.core.config import settings

router = APIRouter(prefix='/api', tags=['settings'])


@router.get('/settings/network', dependencies=[Depends(require_local_admin)])
def get_network_settings():
    return {
        'mode': settings.growora_network_mode,
        'bind_host': settings.bind_host,
        'bind_port': settings.growora_bind_port,
        'allowed_origins': settings.growora_allowed_origins,
        'lan_require_join_code': settings.growora_lan_require_join_code,
        'lan_room_ttl_minutes': settings.growora_lan_room_ttl_minutes,
        'lan_max_clients': settings.growora_lan_max_clients,
        'lan_trusted_subnets': settings.growora_lan_trusted_subnets,
        'lan_rate_limit': settings.growora_lan_rate_limit,
    }
