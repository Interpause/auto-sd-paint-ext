import json
from typing import Any, Dict, List

from krita import QVBoxLayout, QWidget

from ..script import Script

# TODO:
# - modify all widgets (that can) to use Config directly instead of Script
# - ExtLayout that given options: List[dict] creates the respective widgets
#   and links them to the ext_cfg
# - The combobox for selecting the script should be moved to ExtWidget
# - ExtWidget now manages ExtLayout for each script and their visibility
# - ExtWidget initializes only once i.e. when the scripts are loaded
# - NOTE: backend will send empty scripts followed by the real one, have to detect
#   for that


class ExtWidget(QWidget):
    def __init__(self, script: Script, key: str, *args, **kwargs):
        super(ExtWidget, self).__init__(*args, **kwargs)
        self.script = script
        self.cfg_key = key
        self.is_init = False

        meta = self.get_meta()
        if len(meta) > 1:
            self.init_ui()

    def get_meta(self) -> Dict[str, List[dict]]:
        try:
            return json.loads(self.script.ext_cfg(self.cfg_key))
        except:
            return {}

    def init_ui(self):
        if self.is_init:
            return
        self.is_init = True

        for opt in self.get_meta():
            type = opt["type"]
            if type == "None":
                continue
