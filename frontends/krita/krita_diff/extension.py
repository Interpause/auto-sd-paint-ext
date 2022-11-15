from krita import Extension, QTimer

from .defaults import REFRESH_INTERVAL
from .script import script


class SDPluginExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(script.action_update_config)
        self.update_timer.start(REFRESH_INTERVAL)
        script.action_update_config()

    def createActions(self, window):
        txt2img_action = window.createAction(
            "txt2img", "Apply txt2img", "tools/scripts"
        )
        txt2img_action.triggered.connect(lambda: script.action_txt2img())
        img2img_action = window.createAction(
            "img2img", "Apply img2img", "tools/scripts"
        )
        img2img_action.triggered.connect(lambda: script.action_img2img())
        upscale_x_action = window.createAction(
            "img2img_upscale", "Apply img2img upscale", "tools/scripts"
        )
        upscale_x_action.triggered.connect(lambda: script.action_sd_upscale())
        upscale_x_action = window.createAction(
            "img2img_inpaint", "Apply img2img inpaint", "tools/scripts"
        )
        upscale_x_action.triggered.connect(lambda: script.action_inpaint())
        simple_upscale_action = window.createAction(
            "simple_upscale", "Apply simple upscaler", "tools/scripts"
        )
        simple_upscale_action.triggered.connect(lambda: script.action_simple_upscale())
