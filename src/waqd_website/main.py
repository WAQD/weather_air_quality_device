from pathlib import Path
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
import waqd
import waqd.app as app

from waqd.settings.settings import Settings
from .menu.routes import rt as menu_router
from .service.device_connection import (
    websocket_endpoint, get_device_data, send_command_to_device, get_connected_devices
)
from waqd.web.pages.weather_main.routes import rt as weather_router
from .authentication import RequiresLoginException, user_redirect_check

current_path = Path(__file__).parent.resolve()
app.settings = Settings(ini_folder=waqd.user_config_dir)

def _frontend_dist_dir() -> Path:
    return current_path / "frontend" / "dist"

web_app = FastAPI(
    title="WAQD",
    description="WAQD website",
)


@web_app.exception_handler(RequiresLoginException)
async def exception_handler(request, exc):
    return RedirectResponse(url="/public/login")

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

web_app.mount("/static", StaticFiles(directory=str(waqd.assets_path)), name="static")

# Device connection routes
web_app.websocket("/ws/device/{device_id}")(websocket_endpoint)
web_app.get("/api/devices/{device_id}/data")(get_device_data)
web_app.post("/api/devices/{device_id}/command")(send_command_to_device)
web_app.get("/api/devices")(get_connected_devices)

web_app.include_router(menu_router, prefix="/menu")
web_app.include_router(weather_router, prefix="/weather")

# Mount the Vue.js frontend under /ui.
# - /ui/public/* stays unauthenticated (served as-is)
# - everything else under /ui/* requires login (via user_redirect_check)
SERVE_FRONTEND = False
if SERVE_FRONTEND:
    @web_app.get("/public/{full_path:path}")
    async def public_ui(full_path: str):
        dist_dir = _frontend_dist_dir()
        candidate_path = (dist_dir / full_path).resolve()

        # Prevent traversal: only serve from dist_dir
        dist_dir_resolved = dist_dir.resolve()
        if dist_dir_resolved not in candidate_path.parents and candidate_path != dist_dir_resolved:
            return FileResponse(dist_dir / "index.html")

        if candidate_path.is_file():
            return FileResponse(candidate_path)

        return FileResponse(dist_dir / "index.html")


    @web_app.get("/{full_path:path}")
    async def ui_spa(full_path: str, _check=user_redirect_check):
        dist_dir = _frontend_dist_dir()
        candidate_path = (dist_dir / full_path).resolve()

        # Prevent traversal: only serve from dist_dir
        dist_dir_resolved = dist_dir.resolve()
        if dist_dir_resolved not in candidate_path.parents and candidate_path != dist_dir_resolved:
            return FileResponse(dist_dir / "index.html")

        if candidate_path.is_file():
            return FileResponse(candidate_path)

        return FileResponse(dist_dir / "index.html")


