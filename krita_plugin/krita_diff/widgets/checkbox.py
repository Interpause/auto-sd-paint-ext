from functools import partial

from krita import QCheckBox as _QCheckBox

from ..config import Config


class QCheckBox(_QCheckBox):
    def __init__(self, cfg: Config, field_cfg: str, label: str = None, *args, **kwargs):
        """Layout for labelled QLineEdit.

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
