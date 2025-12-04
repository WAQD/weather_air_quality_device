import functools
from functools import lru_cache, partial
from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse
from frozendict import deepfreeze
from htmlmin import minify
from jinja2 import Environment, FileSystemLoader

import waqd
import waqd.app as app
from waqd import DEBUG_LEVEL
from waqd.base.translation import Translation
from waqd.settings import LANG

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


def base_template(file_name: str, context: dict[str, Any], root_path=current_path, lang_str: str="") -> str:
    # also include the parent, so we can use the components from the main template
    if not lang_str:
        lang_str = app.settings.get_string(LANG) or "en"
    @conditional_lru_cache
    def _get_template(lang_str: str = "en") -> Any:
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

        # Cache busting helper for static files
        def cache_bust(file_path: str) -> str:
            """Add cache busting query parameter to static files"""
            try:
                # Use app version as cache buster for CSS and other assets
                return f"{file_path}?v={waqd.__version__}"
            except Exception:
                return file_path

        # Make available in all templates
        template_env.globals["t"] = _t
        template_env.globals["cache_bust"] = cache_bust
        return template_env.get_template(file_name)

    return extra_minify(_get_template(lang_str=lang_str).render(context))


def render_main(
    content: str, user: None=None, overflow=True, toast="", root_path=current_path
    , menu: bool=True, local: bool=True, logged_in: bool=True, theme_color: str=""
) -> HTMLResponse:
    """if overflow is false, on the RPI itself it will not scroll"""
    overflow_config = ""
    if not overflow:
        overflow_config = "overflow-scroll md:overflow-hidden lg:overflow-scroll"
    if not theme_color:
        if app.settings:
            theme_color = app.settings.get_string("theme_color")
        else:
            theme_color = "purple"
    # if menu:
    #     menu_content = base_template(
    #         "menu/views/menu.html",
    #         {
    #             "local": local,
    #             "logged_in": logged_in,
    #         },
    #         current_path,
    #     )
    tpl = base_template(
        "views/index.html",
        {
            # "menu_content": menu_content if menu else "",
            "content": content,
            "overflow_config": overflow_config,
            "toast": toast,
            "local": local,
            "theme_color": theme_color,
            "version": waqd.__version__,  # Add version for cache busting in main template
        },
        root_path,
    )
    return HTMLResponse(content=extra_minify(tpl), status_code=200)
