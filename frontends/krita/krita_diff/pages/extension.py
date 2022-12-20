import json
from functools import partial
from typing import List

from krita import QVBoxLayout, QWidget

from ..config import Config
from ..script import script
from ..utils import get_ext_key
from ..widgets import (
    QCheckBox,
    QComboBoxLayout,
    QLineEditLayout,
    QMultiCheckBoxLayout,
    QSpinBoxLayout,
)


# TODO: dynamically adjust script options available without needing to restart plugin
class ExtWidget(QWidget):
    def __init__(self, ext_cfg: Config, ext_type: str, ext_name: str, *args, **kwargs):
        """Dynamically create form for script based on metadata.

        Args:
            ext_cfg (Config): Config object to get metadata from.
            ext_type (str): Whether metadata is in "scripts_txt2img", "scripts_img2img" or "scripts_inpaint"
            ext_name (str): Name of script.
        """
        super(ExtWidget, self).__init__(*args, **kwargs)

        get_key = partial(get_ext_key, ext_type, ext_name)
        
        try:
            meta: List[dict] = json.loads(ext_cfg(get_key()))
        except json.JSONDecodeError:
            meta = []
            print(f"Script metadata is invalid: {ext_cfg(get_key())}")

        layout = QVBoxLayout()
        self.widgets = []
        for i, o in enumerate(meta):
            w = None
            k = get_key(i)
            if o["type"] == "range":
                w = QSpinBoxLayout(
                    ext_cfg,
                    k,
                    label=o["label"],
                    min=o["min"],
                    max=o["max"],
                    step=o["step"],
                )
            elif o["type"] == "combo":
                w = QComboBoxLayout(ext_cfg, o["opts"], k, label=o["label"])
            elif o["type"] == "text":
                w = QLineEditLayout(ext_cfg, k, o["label"])
            elif o["type"] == "checkbox":
                w = QCheckBox(ext_cfg, k, o["label"])
            elif o["type"] == "multiselect":
                w = QMultiCheckBoxLayout(ext_cfg, o["opts"], k, o["label"])
            else:
                continue
            self.widgets.append(w)
            if isinstance(w, QWidget):
                layout.addWidget(w)
            else:
                layout.addLayout(w)
        self.setLayout(layout)

    def cfg_init(self):
        for w in self.widgets:
            w.cfg_init()

    def cfg_connect(self):
        for w in self.widgets:
            w.cfg_connect()


class ExtSectionLayout(QVBoxLayout):
    def __init__(self, cfg_prefix: str, *args, **kwargs):
        super(ExtSectionLayout, self).__init__(*args, **kwargs)

        # NOTE: backend will send empty scripts followed by the real one, have to
        # detect for that
        self.is_init = False

        self.dropdown = QComboBoxLayout(
            script.cfg,
            f"{cfg_prefix}_script_list",
            f"{cfg_prefix}_script",
            label="(Experimental) Scripts:",
        )
        self.addLayout(self.dropdown)

        self.ext_type = f"scripts_{cfg_prefix}"
        self.ext_names = partial(script.cfg, f"{cfg_prefix}_script_list", "QStringList")
        self.ext_widgets = {}
        self.init_ui_once_if_ready()

    def init_ui_once_if_ready(self):
        """Init UI only once, and only when its ready (aka metadata is present)."""
        if self.is_init:
            return
        if len(self.ext_names()) != script.ext_cfg(f"{self.ext_type}_len", int):
            return

        self.is_init = True
        for ext_name in self.ext_names():
            ext_widget = ExtWidget(script.ext_cfg, self.ext_type, ext_name)
            ext_widget.setVisible(False)
            self.addWidget(ext_widget)
            self.ext_widgets[ext_name] = ext_widget
        self._cfg_connect()

    def cfg_init(self):
        self.dropdown.cfg_init()
        self.init_ui_once_if_ready()
        for widget in self.ext_widgets.values():
            widget.cfg_init()

    def cfg_connect(self):
        self.dropdown.cfg_connect()
        self.init_ui_once_if_ready()
        self.dropdown.qcombo.currentTextChanged.connect(self._update)

    def _update(self, selected):
        for w in self.ext_widgets.values():
            w.setVisible(False)
        widget = self.ext_widgets.get(selected, None)
        if widget:
            widget.setVisible(True)

    def _cfg_connect(self):
        for widget in self.ext_widgets.values():
            widget.cfg_connect()
        self._update(self.dropdown.qcombo.currentText())
