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
            # read filetoc.json
            with open(str(dict_file), encoding='utf-8') as f:
                ts_dict = json.load(f)
            self._resources[id] = ts_dict

        # get filetype and filelist
        lang_dict = self._resources[id].get(lang, {})
        if not lang_dict:
            Logger().error(f"TL: Cannot find language string for {lang}")
            return ""

        value = lang_dict.get(key)
        if not value:
            Logger().error("TL: Cannot find resource id %s in catalog", key)
        return value
