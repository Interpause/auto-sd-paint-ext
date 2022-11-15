from functools import partial

from krita import DockWidget, QScrollArea, QTabWidget, QTimer, QVBoxLayout, QWidget

from .defaults import REFRESH_INTERVAL, STATE_INIT, STATE_READY, STATE_URLERROR
from .pages import (
    ConfigTabWidget,
    Img2ImgTabWidget,
    InpaintTabWidget,
    SDCommonWidget,
    Txt2ImgTabWidget,
    UpscaleTabWidget,
)
from .script import script
from .style import style
from .widgets import QLabel

# Notes:
# - Consider making QuickConfig an accordion to save vertical space
#    - There's no accordion in Qt. Cry. I wanna go back to using Preact & JSX...

# TODO:
# - split each tab into its own Docker
# - by default, dock all the tabs onto each other except quick config
# - see https://scripting.krita.org/lessons/docker-widgets
# - Might want to seriously consider drawing the line on what is done by backend/frontend


class SDPluginDocker(DockWidget):
    def __init__(self, *args, **kwargs):
        super(SDPluginDocker, self).__init__(*args, **kwargs)
        self.setWindowTitle("SD Plugin")
        self.create_interfaces()
        script.action_update_config()
        self.update_interfaces()
        self.connect_interfaces()
        self.setWidget(self.widget)

    def create_interfaces(self):
        self.quick_widget = SDCommonWidget()
        self.txt2img_widget = Txt2ImgTabWidget()
        self.img2img_widget = Img2ImgTabWidget()
        self.inpaint_widget = InpaintTabWidget()
        self.upscale_widget = UpscaleTabWidget()
        self.config_widget = ConfigTabWidget(self.update_interfaces)

        self.tabs = tabs = QTabWidget()
        tabs.addTab(self.txt2img_widget, "Txt2Img")
        tabs.addTab(self.img2img_widget, "Img2Img")
        tabs.addTab(self.inpaint_widget, "Inpaint")
        tabs.addTab(self.upscale_widget, "Upscale")
        tabs.addTab(self.config_widget, "Config")
        tabs.setTabPosition(QTabWidget.West)

        self.status_bar = QLabel()
        self.update_status_bar(STATE_INIT)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.quick_widget)
        layout.addWidget(self.status_bar)
        layout.addWidget(tabs)
        layout.addStretch()

        self.widget = QScrollArea()
        self.widget.setStyleSheet(style)
        widget = QWidget(self)
        widget.setLayout(layout)
        self.widget.setWidget(widget)
        self.widget.setWidgetResizable(True)

        self.update_timer = QTimer()

    def update_interfaces(self):
        self.quick_widget.cfg_init()
        self.txt2img_widget.cfg_init()
        self.img2img_widget.cfg_init()
        self.inpaint_widget.cfg_init()
        self.upscale_widget.cfg_init()
        self.config_widget.cfg_init()

        self.tabs.setCurrentIndex(script.cfg("tab_index", int))

    def connect_interfaces(self):
        self.quick_widget.cfg_connect()
        self.txt2img_widget.cfg_connect()
        self.img2img_widget.cfg_connect()
        self.inpaint_widget.cfg_connect()
        self.upscale_widget.cfg_connect()
        self.config_widget.cfg_connect()

        self.update_timer.timeout.connect(script.action_update_config)
        self.update_timer.start(REFRESH_INTERVAL)
        script.status_changed.connect(self.update_status_bar)
        script.config_updated.connect(self.update_interfaces)
        self.tabs.currentChanged.connect(partial(script.cfg.set, "tab_index"))

    def update_status_bar(self, s):
        if s == STATE_READY and STATE_URLERROR not in self.status_bar.text():
            return
        self.status_bar.setText(f"<b>Status:</b> {s}")

    def canvasChanged(self, canvas):
        pass
