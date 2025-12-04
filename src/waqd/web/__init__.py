import os
import subprocess
from time import sleep

import waqd

browser_proc = None
LOCAL_SERVER_PORT = "8080"


def start_web_server(reload=False):
    import uvicorn

    os.system("sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.13")

    if reload:
        hostname = "localhost"
    else:
        hostname = "0.0.0.0"

    uvicorn.run(
        "waqd.web.main:web_app",
        host=hostname,
        port=80,
        reload=reload,
        reload_excludes=["*.html", "*.css", ".log"],
    )
    if browser_proc is not None:
        browser_proc.terminate()


def start_web_ui_chromium_kiosk_mode():
    # Start Chromium in kiosk mode
    sleep(5)  # wait a little bit so the hw is not overwhelmed and loading in shorter
    global browser_proc
    browser_proc = subprocess.Popen(
        [
            "chromium",
            "--kiosk",
            "--noerrdialogs",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--disable-restore-session-state",
            "--disable-translate",
            "--disable-pinch",
            "--disable-features=TranslateUI",
            f"http://localhost:{LOCAL_SERVER_PORT}/login_admin.html",
            "--force-device-scale-factor=0.8",
        ]
    )


def start_web_ui_firefox_kiosk_mode():  # start_web_ui_firefox_kiosk_mode():
    # Start Firefox in kiosk mode
    sleep(5)  # wait a little bit so the hw is not overwhelmed and loading in shorter

    # Create Firefox profile with scaling and touch preferences
    profile_path = waqd.user_config_dir / "firefox_profile"
    profile_path.mkdir(exist_ok=True)
    user_js = profile_path / "user.js"
    user_js.write_text(
        'user_pref("layout.css.devPixelsPerPx", "0.8");\n'
        'user_pref("browser.cache.disk.enable", false);\n'
        'user_pref("browser.cache.memory.enable", true);\n'
        'user_pref("dom.w3c_touch_events.enabled", 1);\n'
        'user_pref("apz.allow_double_tap_zooming", false);\n'
        'user_pref("apz.allow_zooming", false);\n'
        'user_pref("ui.click_hold_context_menus", false);\n'
        'user_pref("layout.css.touch_action.enabled", true);\n'
        'user_pref("apz.touch_start_tolerance", "0.1");\n'
        'user_pref("apz.drag.enabled", false);\n'
        'user_pref("ui.textSelectBackgroundAttention", "transparent");\n'
        'user_pref("layout.word_select.eat_space_to_next_word", false);\n'
    )

    global browser_proc
    browser_proc = subprocess.Popen(
        [
            "firefox",
            "--kiosk",
            "--profile",
            str(profile_path),
            f"http://localhost:{LOCAL_SERVER_PORT}/login_admin.html",
        ],
        env={**os.environ, "MOZ_DISABLE_CONTENT_SANDBOX": "1"},
    )
