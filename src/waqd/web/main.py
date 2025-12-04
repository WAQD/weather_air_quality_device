from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import waqd
import waqd.app as app
from waqd.base.file_logger import Logger

from .api.sensor.v1.routes import rt as sensor_v1_router
from .api.weather.v1.routes import rt as weather_v1_router
from .menu.routes import rt as menu_router
from .pages.network_mgr.routes import rt as network_mgr
from .pages.settings.routes import rt as settings_router
from .pages.weather_main.routes import rt as weather_router

current_path = Path(__file__).parent.resolve()


web_app = FastAPI(
    title="Waqd Web UI",
    description="Web UI for Waqd",
    version=waqd.__version__,
    debug=waqd.DEBUG_LEVEL > 0,
)

web_app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@web_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    Logger().error(f"{request}: {exc_str}")
    content = {"status_code": 10422, "message": exc_str, "data": None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


# HTML routers
# Public routes
web_app.mount("/static", StaticFiles(directory=str(waqd.assets_path)), name="static")
web_app.include_router(menu_router, prefix="/menu")

web_app.include_router(
    weather_router,
    prefix="/weather",
)
web_app.include_router(
    settings_router,
    prefix="/settings",
)

web_app.include_router(
    network_mgr,
    prefix="/network_mgr",
)

# API routers
web_app.include_router(
    weather_v1_router,
    prefix="/api/weather/v1",
)
web_app.include_router(
    sensor_v1_router,
    prefix="/api/sensor/v1",
)


@web_app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/weather")


if app.comp_ctrl is None:
    app.basic_setup()
