import functools
from functools import lru_cache, partial
from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse
from frozendict import deepfreeze
from htmlmin import minify
from jinja2 import Environment, FileSystemLoader

import waqd.app as app
from waqd import DEBUG_LEVEL
from waqd.settings import LANG

from .authentication import PermissionChecker, UserInDB
from waqd.base.translation import Translation

extra_minify = partial(minify, remove_comments=True, remove_empty_space=True)
current_path = Path(__file__).parent.resolve()


def conditional_lru_cache(func):
    if DEBUG_LEVEL < 1:
        return lru_cache()(func)
    return func


def freezeargs(func):
    """Decorator to freeze mutable arguments (like dicts) to make them hashable for caching."""

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        args = (deepfreeze(arg) if isinstance(arg, dict) else arg for arg in args)
        kwargs = {k: deepfreeze(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
        return func(*args, **kwargs)

    return wrapped


@freezeargs
@conditional_lru_cache
def sub_template(
    file_name: str, context: dict[str, Any], root_path: Path, component=False
) -> str:
    if component:
        root_path = root_path / "components"
    else:
        root_path = root_path / "views"
    return base_template(file_name, context, root_path)


def base_template(file_name: str, context: dict[str, Any], root_path=current_path) -> str:
    # also include the parent, so we can use the components from the main template

    @conditional_lru_cache
    def _get_template():
        template_loader = FileSystemLoader(searchpath=[str(root_path), str(root_path.parent)])
        template_env = Environment(loader=template_loader)
        # Expose a lightweight translation helper backed by JSON catalogs
        def _t(key: str, /, **kwargs):
            """Translate a UI key using assets/base/ui_dict.json and format with kwargs.

            Usage in templates:
              {{ t('motion_reg') }}
              {{ t('new_pw_text', user_name=user_name, pw=pw) }}
            """
            try:
                lang_str: str = "en"
                # app.settings may store the language; Translation handles mapping
                if hasattr(app, "settings"):
                    # tolerate missing key gracefully
                    lang_str = app.settings.get_string(LANG)
                text = Translation().get_localized_string(
                    asset_id="ui_dict.json",
                    key=key,
                    lang=lang_str,
                    asset_dir="base",
                ) or ""
                if kwargs:
                    try:
                        return text.format(**kwargs)
                    except Exception:
                        # If formatting fails (e.g., missing kw), return raw text
                        return text
                return text
            except Exception:
                return ""

        # Make available in all templates
        template_env.globals["t"] = _t
        return template_env.get_template(file_name)

    return extra_minify(_get_template().render(context))


def render_main(
    content: str, user: UserInDB | None, overflow=True, toast="", root_path=current_path
    , menu: bool=True
) -> HTMLResponse:
    """if overflow is false, on the RPI itself it will not scroll"""
    overflow_config = ""
    if not overflow:
        overflow_config = "overflow-scroll md:overflow-hidden lg:overflow-scroll"

    local = False
    if user:
        local = PermissionChecker(
            required_permissions=[
                "users:local",
            ]
        ).check_permissions(user)
    if menu:
        menu_content = base_template(
            "menu/views/menu.html",
            {
                "local": local,
                "logged_in": bool(user),
            },
            current_path,
        )
    tpl = base_template(
        "views/index.html",
        {
            "menu_content": menu_content if menu else "",
            "content": content,
            "overflow_config": overflow_config,
            "toast": toast,
            "local": local,
            "theme_color": app.settings.get("theme_color"),
        },
        root_path,
    )
    return HTMLResponse(content=extra_minify(tpl), status_code=200)
