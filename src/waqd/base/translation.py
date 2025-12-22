import json
from waqd.settings import LANG_ENGLISH
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
            Logger().error(f"TL: Cannot find resource id {key} in catalog")
            return ""

        value = key_dict.get(lang)
        if not value:
            # Fallback to English if translation not found
            value = key_dict.get(LANG_ENGLISH, "")
            if not value:
                Logger().error(f"TL: Cannot find translation for {key} in {lang}")
        return value
