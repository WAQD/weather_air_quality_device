import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from .service.device_connection import (
    websocket_endpoint, get_device_data, send_command_to_device, get_connected_devices
)
from .auth.authentication import RequiresLoginException, user_redirect_check, admin_check
from .api.public.routes import rt as public_router
from .api.user.routes import rt as user_router

BASE_PATH = Path(__file__).parent.resolve()
ASSETS_PATH = BASE_PATH.parent / "waqd" / "assets"
FRONTEND_DIST_DIR = BASE_PATH / "ui" / "dist"

web_app = FastAPI(
    title="WAQD",
    description="WAQD website",
)


@web_app.exception_handler(RequiresLoginException)
async def exception_handler(request, exc):
    return RedirectResponse(url="/login")

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

web_app.mount("/static", StaticFiles(directory=str(ASSETS_PATH)), name="static")

# Device connection routes
web_app.websocket("/ws/device/{device_id}")(websocket_endpoint)
web_app.get("/api/devices/{device_id}/data")(get_device_data)
web_app.post("/api/devices/{device_id}/command")(send_command_to_device)
web_app.get("/api/devices")(get_connected_devices)

web_app.include_router(public_router, prefix="/api/public")
web_app.include_router(user_router, prefix="/api/user")

# Mount the Vue.js frontend under /ui.
# - /ui/public/* stays unauthenticated (served as-is)
# - everything else under /ui/* requires login (via user_redirect_check)
SERVE_FRONTEND = bool(os.getenv("SERVE_FRONTEND", False))
if SERVE_FRONTEND:
    @web_app.get("/admin")
    async def admin_page(_check=admin_check):
        """Admin page - requires admin permissions"""
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    @web_app.get("/public/{full_path:path}")
    async def public_ui(full_path: str):
        candidate_path = (FRONTEND_DIST_DIR / full_path).resolve()

        # Prevent traversal: only serve from dist_dir
        dist_dir_resolved = FRONTEND_DIST_DIR.resolve()
        if dist_dir_resolved not in candidate_path.parents and candidate_path != dist_dir_resolved:
            return FileResponse(FRONTEND_DIST_DIR / "index.html")

        if candidate_path.is_file():
            return FileResponse(candidate_path)

        return FileResponse(FRONTEND_DIST_DIR / "index.html")


    @web_app.get("/{full_path:path}")
    async def ui_spa(full_path: str, _check=user_redirect_check):
        dist_dir = FRONTEND_DIST_DIR
        candidate_path = (dist_dir / full_path).resolve()

        # Prevent traversal: only serve from dist_dir
        dist_dir_resolved = dist_dir.resolve()
        if dist_dir_resolved not in candidate_path.parents and candidate_path != dist_dir_resolved:
            return FileResponse(dist_dir / "index.html")

        if candidate_path.is_file():
            return FileResponse(candidate_path)

        return FileResponse(dist_dir / "index.html")


