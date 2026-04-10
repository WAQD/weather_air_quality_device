# import at the end, to avoid circular imports
from waqd.settings.settings import Settings

# Shared settings names

LANG = "lang"
LANG_GERMAN = "de"
LANG_ENGLISH = "en"
LANG_HUNGARIAN = "hu"

__all__ = ["Settings"]
