from pathlib import Path

import bcrypt
from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

import waqd
import waqd.app as app
from waqd import __version__ as WAQD_VERSION
from waqd.base.file_logger import Logger
from waqd.base.system import RuntimeSystem
from waqd.components.weather.base_types import Location
from waqd.components.weather.open_meteo import OpenMeteo
from waqd.settings import (
    BRIGHTNESS,
    LOCATION_ALTITUDE_M,
    LOCATION_COUNTRY_CODE,
    LOCATION_LATITUDE,
    LOCATION_LONGITUDE,
    LOCATION_NAME,
    LOCATION_STATE,
    USER_DEFAULT_PW,
)
from waqd.web.templates import render_main, sub_template

rt = APIRouter()

current_path = Path(__file__).parent.resolve()


@rt.get("/", response_class=HTMLResponse)
async def settings():
    app.comp_ctrl.unload_all()
    context = app.settings.get_all()
    content = sub_template(
        "settings.html",
        context,
        current_path,
    )
    return render_main(content)


@rt.get("/location_search_result", response_class=HTMLResponse)
async def location_search_result(query: str):
    # request to the Open-Meteo Geocoding API
    location_data = OpenMeteo().find_location_candidates(query, lang="en")
    if not location_data:
        return HTMLResponse("No location found")
    return sub_template(
        "snippets/location_result.html",
        {"location_data": location_data},
        current_path,
        component=True,
    )

@rt.get("/new_release_available", response_class=HTMLResponse)
async def new_release_available():
    try:
        latest_version, update_available = app.comp_ctrl.components.auto_updater.check_newer_version()
    except Exception as e:
        Logger().debug("Failed to check for updates: %s", e)
        return HTMLResponse("Failed to check update information. Try again later!")
    if not update_available:
        return sub_template(
            "snippets/no_new_release.html",
            {},
            current_path,
            component=True,
        ) 
    assert latest_version
    version = latest_version.title
    if latest_version.prerelease:
        version += f"({latest_version.tag_name} - currently on: {WAQD_VERSION})"
    return sub_template(
        "snippets/latest_release_info.html",
        {"version": version, "content": latest_version.body.splitlines()},
        current_path,
        component=True,
    )

@rt.post("/trigger_update", response_class=HTMLResponse)
async def trigger_update():
    try:
        assert app.comp_ctrl.components.auto_updater.latest_release is not None
        app.comp_ctrl.components.auto_updater.install_update(
            app.comp_ctrl.components.auto_updater.latest_release.tag_name
        )
        return HTMLResponse("Update started. Please wait for the device to restart.")
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)

@rt.post("/set", response_class=HTMLResponse)
async def set_setting(name: str = Form(), value=Form()):
    try:
        app.settings.set(name, value)
        # apply settings immediately if needed
        if name == BRIGHTNESS: # instant set settings
            app.comp_ctrl.components.display.set_brightness(int(value))
        return HTMLResponse("Set ☑")
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)


@rt.post("/set/location", response_class=HTMLResponse)
async def set_location(
    location: Location
):
    try:
        app.settings.set(LOCATION_NAME, location.name)
        app.settings.set(LOCATION_LATITUDE, location.latitude)
        app.settings.set(LOCATION_LONGITUDE, location.longitude)
        app.settings.set(LOCATION_COUNTRY_CODE, location.country_code)
        app.settings.set(LOCATION_ALTITUDE_M, location.altitude)
        app.settings.set(LOCATION_STATE, location.state)

        return HTMLResponse("Set ☑")
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)

@rt.post("/reset_pw", response_class=HTMLResponse)
async def reset_pw():
    try:
        pw = bcrypt.gensalt(4).decode("utf-8")[18:]
        app.settings.set(USER_DEFAULT_PW, pw)
        username = "remote_user"
        return HTMLResponse(f"Username: {username} <br/> password: {pw}", status_code=200)
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)

@rt.get("/about", response_class=HTMLResponse)
async def about():
    content = sub_template(
        "about.html",
        {"version": waqd.__version__, "platform": RuntimeSystem().platform},
        current_path,
    )
    return content
