from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from waqd.base.system import RuntimeSystem

rt = APIRouter()

current_path = Path(__file__).parent.resolve()

@rt.get("/network_icon", response_class=HTMLResponse)
async def wifi_signal_strength(
):
    from waqd.base.network import Network
    network = Network()
    icon_name = "cloud_off"
    if network.is_connected_via_eth():
        icon_name = "lan"
    elif network.is_connected_via_wlan():
        strength = network.current_wifi_strength()
        if strength:
            if 75 < strength <= 100:
                icon_name = "wifi_full"
            elif strength > 50:
                icon_name = "wifi_2_bar"
            else:
                icon_name = "wifi_1_bar"
    image = f"""<svg viewBox="0 0 24 24" class="h-8">
    <use href="/static/general_icons/{icon_name}.svg#main" fill="white"/></svg>"""
    return HTMLResponse(image)


@rt.post("/shutdown", response_class=HTMLResponse)
async def shutdown():
    RuntimeSystem().shutdown()
    

@rt.post("/restart", response_class=HTMLResponse)
async def restart():
    RuntimeSystem().restart()
