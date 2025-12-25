from functools import lru_cache
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from waqd import DEBUG_LEVEL

from .service.device_connection import (
    websocket_endpoint,
    user_device_stream,
    get_device_data,
    get_connected_devices,
)
from .auth.authentication import (
    ADMIN_PERMISSION,
    RequiresLoginException,
    user_redirect_check,
    admin_check,
)
from .api.public.routes import rt as public_router
from .api.user.routes import rt as user_router
from .api.device.routes import rt as device_router
from .database.user import add_user, get_all_users

BASE_PATH = Path(__file__).parent.resolve()
ASSETS_PATH = BASE_PATH.parent / "waqd" / "assets"
FRONTEND_DIST_DIR = BASE_PATH / "ui" / "dist"

# Generate default admin user if not exists

if not any(u.username == "admin" for u in get_all_users()):
    pw = os.getenv("WAQD_ADMIN_PASSWORD", "admin12345")
    add_user(username="admin", password=pw, permissions=[ADMIN_PERMISSION])
    print("Created default admin user with username 'admin' and password:", pw)

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

web_app.mount("/static", StaticFiles(directory=str(ASSETS_PATH)), name="static")

# Device connection routes
web_app.websocket("/ws/device/{device_id}")(websocket_endpoint)
web_app.websocket("/ws/user/device/{device_id}")(user_device_stream)
web_app.get("/api/devices/{device_id}/data")(get_device_data)
web_app.get("/api/devices")(get_connected_devices)

web_app.include_router(public_router, prefix="/api/public")
web_app.include_router(user_router, prefix="/api/user")
web_app.include_router(device_router, prefix="/api/user")

# Root redirect - register early
@web_app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect root to /public/home"""
    return RedirectResponse(url="/public/home")

# Mount the Vue.js frontend under /ui.
# - /public/* stays unauthenticated (served as-is)
# - everything else requires login (via user_redirect_check)
if DEBUG_LEVEL == 0:
    # Static assets from dist - must come before catch-all
    @web_app.get("/assets/{full_path:path}")
    async def assets(full_path: str):
        return resolve_path("assets/" + full_path)

    # Catch-all route - must come last
    @web_app.get("/{full_path:path}")
    async def root_files(full_path: str):
        """Serve static files or SPA"""
        return resolve_path(full_path)

    def resolve_path(full_path: str):
        dist_dir = FRONTEND_DIST_DIR
        candidate_path = (dist_dir / full_path).resolve()

        # Prevent traversal: only serve from dist_dir
        dist_dir_resolved = dist_dir.resolve()
        if (
            dist_dir_resolved not in candidate_path.parents
            and candidate_path != dist_dir_resolved
        ):
            return FileResponse(dist_dir / "index.html")

        if candidate_path.is_file():
            return FileResponse(candidate_path)

        return FileResponse(dist_dir / "index.html")
