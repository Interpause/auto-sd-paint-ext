from typing import List

from krita import QVBoxLayout

from .misc import QLabel


class TipsLayout(QVBoxLayout):
    def __init__(self, tips: List[str], prefix="<em>Tip:</em> ", *args, **kwargs):
        super(TipsLayout, self).__init__(*args, **kwargs)

        self.tips = [QLabel(prefix + t) for t in tips]
        for t in self.tips:
            self.addWidget(t)

    def setVisible(self, visible: bool):
        for t in self.tips:
            t.setVisible(visible)
