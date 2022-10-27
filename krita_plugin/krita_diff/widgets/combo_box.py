from functools import partial
from typing import Union

from krita import QComboBox, QHBoxLayout

from ..config import Config
from .misc import QLabel


class QComboBoxLayout(QHBoxLayout):
    def __init__(
        self,
        cfg: Config,
        options_cfg: Union[str, list],
        selected_cfg: str,
        label: str = None,
        num_chars: int = None,
        *args,
        **kwargs
    ):
        """Layout for labelled QComboBox.

        Args:
            cfg (Config): Config to connect to.
            options_cfg (Union[str, list]): Config key to read available options from or list of options.
            selected_cfg (str): Config key to read/write selected option to.
            label (str, optional): Label, uses `selected_cfg` if None. Defaults to None.
            num_chars (int, optional): Max length of qcombo in chars. Defaults to None.
        """
        super(QComboBoxLayout, self).__init__(*args, **kwargs)
        self.num_chars = num_chars

        # Used to connect to config stored in script
        self.cfg = cfg
        self.options_cfg = options_cfg
        self.selected_cfg = selected_cfg
        self._items = set()

        self.qlabel = QLabel(self.selected_cfg if label is None else label)
        self.qcombo = QComboBox()

        self.addWidget(self.qlabel)
        self.addWidget(self.qcombo)

    def cfg_init(self):
        # prevent value from getting wiped
        val = self.cfg(self.selected_cfg, str)
        opts = set(
            self.cfg(self.options_cfg, "QStringList")
            if isinstance(self.options_cfg, str)
            else self.options_cfg
        )
        # prevent dropdown from closing when cfg_init is called by update
        if opts != self._items:
            self._items = opts
            self.qcombo.clear()
            self.qcombo.addItems(list(opts))

        # doesn't throw error if val is not in options; good for us
        self.qcombo.setCurrentText(val)
        if self.num_chars is not None:
            self.qcombo.setFixedWidth(
                self.qcombo.fontMetrics().width("M" * self.num_chars)
            )

    def cfg_connect(self):
        self.qcombo.currentTextChanged.connect(partial(self.cfg.set, self.selected_cfg))
