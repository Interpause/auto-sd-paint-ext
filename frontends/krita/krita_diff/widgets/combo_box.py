from functools import partial
from typing import Union

from krita import QComboBox, QHBoxLayout, Qt, QValidator

from ..config import Config
from .misc import QLabel


class QOptionValidator(QValidator):
    def __init__(self, opts: set, *args, **kwargs):
        super(QOptionValidator, self).__init__(*args, **kwargs)
        self.opts = opts

    def validate(self, input, pos):
        # Below validation rules make it impossible to type invalid options
        if len(self.opts) < 2:
            # List hasn't loaded yet
            return QValidator.Intermediate, input, pos
        elif input in self.opts:
            return QValidator.Acceptable, input, pos
        elif any(o.find(input) == 0 for o in self.opts):
            return QValidator.Intermediate, input, pos
        else:
            return QValidator.Invalid, input, pos

    def fixup(self, input):
        return ""


class QComboBoxLayout(QHBoxLayout):
    def __init__(
        self,
        cfg: Config,
        options_cfg: Union[str, list],
        selected_cfg: str,
        label: str = None,
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

        # Used to connect to config stored in script
        self.cfg = cfg
        self.options_cfg = options_cfg
        self.selected_cfg = selected_cfg
        self._items = set()

        self.qlabel = QLabel(self.selected_cfg if label is None else label)
        self.qcombo = QComboBox()
        self.qcombo.view().setTextElideMode(Qt.ElideLeft)
        self.qcombo.setEditable(True)
        self.qcombo.setInsertPolicy(QComboBox.NoInsert)
        self.qcombo.setMinimumWidth(10)

        self.addWidget(self.qlabel)
        self.addWidget(self.qcombo)

    def cfg_init(self):
        opts = sorted(
            set(
                self.cfg(self.options_cfg, "QStringList")
                if isinstance(self.options_cfg, str)
                else self.options_cfg
            ),
            key=str.casefold,
        )

        # NOTE: assumes the None option will always be labelled as "None"
        if "None" in opts:
            opts.remove("None")
            opts.insert(0, "None")

        # prevent dropdown from closing when cfg_init is called by update
        if set(opts) != self._items:
            self._items = set(opts)
            # as using editable mode, text isn't affected by clearing options
            self.qcombo.clear()
            self.qcombo.addItems(opts)
            self.qcombo.setValidator(QOptionValidator(self._items))

        # avoid resetting the auto-completer
        if self.qcombo.currentText() != self.cfg(self.selected_cfg):
            self.qcombo.setEditText(self.cfg(self.selected_cfg))

    def cfg_connect(self):
        # Possible to get invalid by backspacing after selecting option
        # but no one would do that deliberately
        self.qcombo.editTextChanged.connect(partial(self.cfg.set, self.selected_cfg))
