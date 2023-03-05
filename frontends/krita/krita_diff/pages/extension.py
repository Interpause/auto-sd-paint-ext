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
            try:
                w.cfg_connect()
            except TypeError:
                pass # Invalid config should resolves itself on next sync.


class ExtSectionLayout(QVBoxLayout):
    def __init__(self, cfg_prefix: str, *args, **kwargs):
        super(ExtSectionLayout, self).__init__(*args, **kwargs)

        self.dropdown = QComboBoxLayout(
            script.cfg,
            f"{cfg_prefix}_script_list",
            f"{cfg_prefix}_script",
            label="Scripts:",
        )
        self.addLayout(self.dropdown)

        self.ext_type = f"scripts_{cfg_prefix}"
        self.ext_names = partial(script.cfg, f"{cfg_prefix}_script_list", "QStringList")
        self.ext_widgets = {}

    def _clear_ext_widgets(self):
        """Properly delete all existing extension widgets."""
        while len(self.ext_widgets) > 0:
            _, widget = self.ext_widgets.popitem()
            self.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()

    def _init_ext_widgets(self):
        """Inits the UI, can be called multiple times if the ext scripts available changed."""
        self._clear_ext_widgets()
        for ext_name in self.ext_names():
            widget = ExtWidget(script.ext_cfg, self.ext_type, ext_name)
            widget.setVisible(False)
            self.addWidget(widget)
            self.ext_widgets[ext_name] = widget
            widget.cfg_connect()

    def cfg_init(self):
        self.dropdown.cfg_init()
        if set(self.ext_names()) != set(self.ext_widgets.keys()):
            self._init_ext_widgets()
        for widget in self.ext_widgets.values():
            widget.cfg_init()

    def cfg_connect(self):
        self.dropdown.cfg_connect()
        self.dropdown.qcombo.currentTextChanged.connect(lambda s: self._update(s))
        self._update(self.dropdown.qcombo.currentText())

    def _update(self, selected):
        """Updates which extension widget is visible."""
        for w in self.ext_widgets.values():
            w.setVisible(False)
        widget = self.ext_widgets.get(selected, None)
        if widget and selected != "None":
            widget.setVisible(True)
