from functools import partial

from krita import QHBoxLayout, QLineEdit

from ..config import Config
from .misc import QLabel


class QLineEditLayout(QHBoxLayout):
    def __init__(
        self,
        cfg: Config,
        field_cfg: str,
        label: str = None,
        placeholder: str = "",
        *args,
        **kwargs
    ):
        """Layout for labelled QLineEdit.

        Args:
            cfg (Config): Config to connect to.
            field_cfg (str): Config key to read/write value to.
            label (str, optional): Label, uses `field_cfg` if None. Defaults to None.
            placeholder (str, optional): Placeholder. Defaults to "".
        """
        super(QLineEditLayout, self).__init__(*args, **kwargs)

        self.cfg = cfg
        self.field_cfg = field_cfg

        self.qedit = QLineEdit()
        self.qedit.setPlaceholderText(placeholder)
        self.addWidget(QLabel(field_cfg if label is None else label))
        self.addWidget(self.qedit)

    def cfg_init(self):
        # NOTE: update timer -> cfg_init, setText seems to reset cursor position so we prevent it
        val = self.cfg(self.field_cfg, str)
        if self.qedit.text() != val:
            self.qedit.setText(val)

    def cfg_connect(self):
        self.qedit.textChanged.connect(partial(self.cfg.set, self.field_cfg))
