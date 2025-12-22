import json
import datetime
from waqd.settings import LANG_ENGLISH, LANG_GERMAN, LANG_HUNGARIAN
from waqd.assets import get_asset_file
from waqd.base.file_logger import Logger

# Runtime translations

class Translation():
    _instance = None
    _resources = {}
    
    # Hardcoded weekday names for supported languages
    _WEEKDAYS = {
        LANG_ENGLISH: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        LANG_GERMAN: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        LANG_HUNGARIAN: ["H", "K", "Sze", "Cs", "P", "Szo", "V"],
    }
    
    # Hardcoded month names for supported languages
    _MONTHS = {
        LANG_ENGLISH: [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ],
        LANG_GERMAN: [
            "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
            "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"
        ],
        LANG_HUNGARIAN: [
            "Jan", "Feb", "Már", "Ápr", "Máj", "Jún",
            "Júl", "Aug", "Szep", "Okt", "Nov", "Dec"
        ],
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_localized_string(self, asset_id: str, key: str, lang=LANG_ENGLISH, asset_dir="base") -> str:
        id = asset_dir + "/" + asset_id
        if id not in self._resources.keys():
            dict_file = get_asset_file(asset_dir, asset_id)
            # read ui_dict.json
            with open(str(dict_file), encoding='utf-8') as f:
                ts_dict = json.load(f)
            self._resources[id] = ts_dict

        # get the key and its translations
        key_dict = self._resources[id].get(key, {})
        if not key_dict:
            Logger().error("TL: Cannot find resource id %s in catalog", key)
            return ""

        value = key_dict.get(lang)
        if not value:
            # Fallback to English if translation not found
            value = key_dict.get(LANG_ENGLISH, "")
            if not value:
                Logger().error("TL: Cannot find translation for %s in %s", key, lang)
        return value
    
    def get_localized_date(self, date_time: datetime.datetime, lang: str = LANG_ENGLISH) -> str:
        """
        Returns a formatted date conforming to the language.
        Contains weekday name, month and day (without year).
        Format: "Weekday, Month Day" (e.g., "Mon, Jan 15" or "Mo, Jan 15")
        
        Args:
            date_time: The datetime object to format
            lang: Language code (en, de, or hu)
        
        Returns:
            Formatted date string
        """
        # Get weekday (0=Monday, 6=Sunday)
        weekday_idx = date_time.weekday()
        # Get month (1-12, convert to 0-11 for array index)
        month_idx = date_time.month - 1
        
        # Get localized names, fallback to English if language not supported
        weekdays = self._WEEKDAYS.get(lang, self._WEEKDAYS[LANG_ENGLISH])
        months = self._MONTHS.get(lang, self._MONTHS[LANG_ENGLISH])
        
        # Format based on language conventions
        if lang == LANG_HUNGARIAN:
            # Hungarian format: "Month Day, Weekday"
            return f"{months[month_idx]} {date_time.day}, {weekdays[weekday_idx]}"
        else:
            # English and German format: "Weekday, Month Day"
            return f"{weekdays[weekday_idx]}, {months[month_idx]} {date_time.day}"
