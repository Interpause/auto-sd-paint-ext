from functools import partial

from krita import QCheckBox as _QCheckBox
from krita import QHBoxLayout, QVBoxLayout

from ..config import Config
from .misc import QLabel


class QCheckBox(_QCheckBox):
    def __init__(self, cfg: Config, field_cfg: str, label: str = None, *args, **kwargs):
        """QCheckBox compatible with the config system.

        Args:
            cfg (Config): Config to connect to.
            field_cfg (str): Config key to read/write value to.
            label (str): Label, uses `field_cfg` if None. Defaults to None.
        """
        label = field_cfg if label is None else label
        super(QCheckBox, self).__init__(label, *args, **kwargs)

        self.cfg = cfg
        self.field_cfg = field_cfg

    def cfg_init(self):
        self.setChecked(self.cfg(self.field_cfg, bool))

    def cfg_connect(self):
        self.toggled.connect(partial(self.cfg.set, self.field_cfg))


# TODO: adjust number of checkboxes based on options without needing restart


class QMultiCheckBoxLayout(QVBoxLayout):
    def __init__(
        self,
        cfg: Config,
        options_cfg: list,
        selected_cfg: str,
        label: str = None,
        *args,
        **kwargs
    ):
        """Layout for labelled multi-select CheckBox.

        Args:
            cfg (Config): Config to connect to.
            options_cfg (list): List of options.
            selected_cfg (str): Config key to read/write selected options to.
            label (str, optional): Label, uses `selected_cfg` if None. Defaults to None.
        """
        super(QMultiCheckBoxLayout, self).__init__(*args, **kwargs)

        self.cfg = cfg
        self.options_cfg = options_cfg
        self.selected_cfg = selected_cfg

        self.qlabel = QLabel(self.selected_cfg if label is None else label)

        # TODO: flexbox-like row breaking
        self.row = QHBoxLayout()
        self.qcheckboxes = []
        for opt in self.options_cfg:
            checkbox = _QCheckBox(opt)
            self.qcheckboxes.append(checkbox)
            self.row.addWidget(checkbox)

        self.addWidget(self.qlabel)
        self.addWidget(self.row)

    def cfg_init(self):
        val = set(self.cfg(self.selected_cfg, "QStringList"))
        for box in self.qcheckboxes:
            box.setChecked(box.text() in val)

    def cfg_connect(self):
        def update(_):
            selected = [b.text() for b in self.qcheckboxes if b.isChecked()]
            self.cfg.set(self.selected_cfg, selected)

        for box in self.qcheckboxes:
            box.toggled.connect(update)
