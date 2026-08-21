import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from waqd.base.file_logger import Logger

from .api.device.routes import rt as device_router
from .api.public.routes import rt as public_router
from .api.public.widget_routes import rt as widget_router
from .api.user.routes import rt as user_router
from .api.weather.routes import rt as weather_router
from .auth.authentication import (
    ADMIN_PERMISSION,
    RequiresLoginException,
)
from .database import create_db_tables
from .database.user import add_user, get_all_users
from .service.device_con import (
    get_connected_devices,
    get_device_data,
    user_device_stream,
    websocket_endpoint,
)

BASE_PATH = Path(__file__).parent.resolve()
FRONTEND_DIST_DIR = BASE_PATH / "ui" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()
    if not any(u.username == "admin" for u in get_all_users()):
        pw = os.getenv("WAQD_ADMIN_PASSWORD", "admin12345")
        add_user(username="admin", password=pw, permissions=[ADMIN_PERMISSION])
        print("Created default admin user with username 'admin' and password:", pw)
    yield


web_app = FastAPI(
    title="WAQD",
    description="WAQD website",
    lifespan=lifespan,
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

# Device connection routes
web_app.websocket("/ws/device/{device_id}")(websocket_endpoint)
web_app.websocket("/ws/user/device/{device_id}")(user_device_stream)
web_app.get("/api/devices/{device_id}/data")(get_device_data)
web_app.get("/api/devices")(get_connected_devices)

web_app.include_router(public_router, prefix="/api/public")
web_app.include_router(widget_router, prefix="/api/public/widget")
web_app.include_router(user_router, prefix="/api/user")
web_app.include_router(device_router, prefix="/api/user")
web_app.include_router(weather_router, prefix="/api/user/weather")


# Root redirect - register early
@web_app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect root to /public/home"""
    return RedirectResponse(url="/public/home")


@web_app.get("/health/live")
async def liveness():
    """Liveness probe - simple OK response to indicate the app is running."""
    return {"status": "alive"}


@web_app.get("/health/ready")
async def readiness():
    """Readiness probe - verifies essential dependencies are available.

    Currently checks that the user database can be read. Return 503 if
    a dependency check fails so orchestrators can retry.
    """
    try:
        # simple sanity check: can we read users from the database?
        _ = get_all_users()
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"not ready: {exc}")


Logger.GLOBAL_LOGFILE_NAME = "waqd_website.log"
Logger(output_path=BASE_PATH).info("Starting WAQD Website FastAPI app")  # type: ignore
# Mount the Vue.js frontend
Logger().info("Mounting production frontend from %s", FRONTEND_DIST_DIR)
static_path = FRONTEND_DIST_DIR / "static"

# Mount static files BEFORE catch-all routes
web_app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
web_app.mount(
    "/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="assets"
)


# Serve PWA-critical files explicitly
@web_app.get("/manifest.webmanifest")
async def serve_manifest():
    """Serve PWA manifest"""
    manifest_path = FRONTEND_DIST_DIR / "manifest.webmanifest"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="Manifest not found")


@web_app.get("/sw.js")
async def serve_service_worker():
    """Serve service worker"""
    sw_path = FRONTEND_DIST_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(
            sw_path,
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
        )
    raise HTTPException(status_code=404, detail="Service worker not found")


@web_app.get("/workbox-{filename:path}.js")
async def serve_workbox(filename: str):
    """Serve workbox files"""
    wb_path = FRONTEND_DIST_DIR / f"workbox-{filename}.js"
    if wb_path.exists():
        return FileResponse(wb_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Workbox file not found")


@web_app.get("/{filename}.png")
async def serve_pwa_icons(filename: str):
    """Serve PWA icons (pwa-192x192.png, pwa-512x512.png)"""
    if filename.startswith("pwa-"):
        icon_path = FRONTEND_DIST_DIR / f"{filename}.png"
        if icon_path.exists():
            return FileResponse(icon_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Icon not found")


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
    if dist_dir_resolved not in candidate_path.parents and candidate_path != dist_dir_resolved:
        return FileResponse(dist_dir / "index.html")

    if candidate_path.is_file():
        return FileResponse(candidate_path)

    return FileResponse(dist_dir / "index.html")
