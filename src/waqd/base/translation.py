import json
import datetime
from waqd.settings import LANG_ENGLISH, LANG_GERMAN, LANG_HUNGARIAN
from waqd.assets import get_asset_file
from waqd.base.file_logger import Logger

# Runtime translations

class Translation():
    _instance = None
    _resources = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_localized_string(self, asset_id: str, key: str, lang=LANG_ENGLISH, asset_dir="base") -> str:
        # Handle new split locale files (en.json, de.json, hu.json)
        if asset_id == "ui_dict.json":
            # Map language codes to locale filenames
            locale_map = {
                LANG_ENGLISH: "en.json",
                LANG_GERMAN: "de.json", 
                LANG_HUNGARIAN: "hu.json"
            }
            
            locale_file = locale_map.get(lang, "en.json")
            locale_id = f"locales/{locale_file}"
            
            # Load the locale file if not already cached
            if locale_id not in self._resources:
                try:
                    # Try loading from website UI locales (primary location)
                    from pathlib import Path
                    import waqd
                    locale_path = waqd.assets_path.parent / "waqd_website" / "ui" / "src" / "locales" / locale_file
                    
                    if not locale_path.exists():
                        Logger().error("TL: Cannot find locale file %s", locale_path)
                        return ""
                    
                    with open(locale_path, encoding='utf-8') as f:
                        self._resources[locale_id] = json.load(f)
                except Exception as e:
                    Logger().error("TL: Error loading locale file %s: %s", locale_file, e)
                    return ""
            
            # Get the translation directly (split files are already language-first format)
            value = self._resources[locale_id].get(key, "")
            
            if not value and lang != LANG_ENGLISH:
                # Fallback to English
                en_id = "locales/en.json"
                if en_id not in self._resources:
                    from pathlib import Path
                    import waqd
                    en_path = waqd.assets_path.parent / "waqd_website" / "ui" / "src" / "locales" / "en.json"
                    
                    if en_path.exists():
                        with open(en_path, encoding='utf-8') as f:
                            self._resources[en_id] = json.load(f)
                
                value = self._resources.get(en_id, {}).get(key, "")
            
            if not value:
                Logger().error("TL: Cannot find translation for %s in %s", key, lang)
            
            return value
        
        # Handle other asset files (e.g., tts_dict.json) - keep old logic
        id = asset_dir + "/" + asset_id
        if id not in self._resources.keys():
            dict_file = get_asset_file(asset_dir, asset_id)
            # read key-first format JSON
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
        
        # Weekday and month keys
        weekday_keys = [
            "weekday_mon", "weekday_tue", "weekday_wed", "weekday_thu",
            "weekday_fri", "weekday_sat", "weekday_sun"
        ]
        month_keys = [
            "month_jan", "month_feb", "month_mar", "month_apr",
            "month_may", "month_jun", "month_jul", "month_aug",
            "month_sep", "month_oct", "month_nov", "month_dec"
        ]
        
        # Get localized names from translation files
        weekday = self.get_localized_string("ui_dict.json", weekday_keys[weekday_idx], lang)
        month = self.get_localized_string("ui_dict.json", month_keys[month_idx], lang)
        
        # Format based on language conventions
        if lang == LANG_HUNGARIAN:
            # Hungarian format: "Month Day, Weekday"
            return f"{month} {date_time.day}, {weekday}"
        else:
            # English and German format: "Weekday, Month Day"
            return f"{weekday}, {month} {date_time.day}"
