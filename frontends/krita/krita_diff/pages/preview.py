from krita import QPixmap, QPushButton, QVBoxLayout, QWidget

from ..script import script
from ..utils import b64_to_img
from ..widgets import QLabel, StatusBar


class PreviewPage(QWidget):
    name = "Live Preview"

    def __init__(self, *args, **kwargs):
        super(PreviewPage, self).__init__(*args, **kwargs)

        self.status_bar = StatusBar()
        self.preview = QLabel()
        self.interrupt_btn = QPushButton("Interrupt")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.status_bar)
        layout.addWidget(self.interrupt_btn)
        layout.addWidget(self.preview)
        layout.addStretch()
        self.setLayout(layout)

    def cfg_init(self):
        pass

    def _update_image(self, progress):
        try:
            enc = progress["current_image"]
            image = b64_to_img(enc)
            self.preview.setPixmap(QPixmap.fromImage(image))
        except:
            pass

    def cfg_connect(self):
        script.status_changed.connect(lambda s: self.status_bar.set_status(s))
        script.progress_update.connect(lambda p: self._update_image(p))
        self.interrupt_btn.released.connect(lambda: script.action_interrupt())
