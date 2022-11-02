from krita import QHBoxLayout, QPushButton

from ..script import script
from ..widgets import QCheckBox, TipsLayout
from .img_base import ImgTabBaseWidget


class Txt2ImgTabWidget(ImgTabBaseWidget):
    def __init__(self, *args, **kwargs):
        super(Txt2ImgTabWidget, self).__init__(cfg_prefix="txt2img", *args, **kwargs)

        self.highres = QCheckBox(script.cfg, "txt2img_highres", "Highres fix")

        inline_layout = QHBoxLayout()
        inline_layout.addWidget(self.highres)
        inline_layout.addLayout(self.denoising_strength_layout)

        self.tips = TipsLayout(
            [
                "Set base_size and max_size higher for AUTO's txt2img highres fix to work."
            ]
        )

        self.btn = QPushButton("Start txt2img")

        self.layout.addLayout(inline_layout)
        self.layout.addWidget(self.btn)
        self.layout.addLayout(self.tips)
        self.layout.addStretch()

    def cfg_init(self):
        super(Txt2ImgTabWidget, self).cfg_init()
        self.highres.cfg_init()

        self.tips.setVisible(not script.cfg("minimize_ui", bool))

    def cfg_connect(self):
        super(Txt2ImgTabWidget, self).cfg_connect()

        def toggle_highres(enabled):
            # hide/show denoising strength
            self.denoising_strength_layout.qlabel.setVisible(enabled)
            self.denoising_strength_layout.qspin.setVisible(enabled)

        self.highres.cfg_connect()
        self.highres.toggled.connect(toggle_highres)
        toggle_highres(self.highres.isChecked())

        self.btn.released.connect(lambda: script.action_txt2img())
