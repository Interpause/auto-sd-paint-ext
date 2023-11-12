from krita import Extension, QMainWindow, QTimer

from .defaults import REFRESH_INTERVAL
from .script import script


class SDPluginExtension(Extension):
    def __init__(self, instance):
        super().__init__(instance)

        self.instance = instance
        # store original window docker config
        self.dock_opts = None

    def setup(self):
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(lambda: script.action_update_config())
        self.update_timer.start(REFRESH_INTERVAL)
        script.config_updated.connect(lambda: self.update_global())
        self.instance.notifier().windowCreated.connect(lambda: self.update_global())
        script.action_update_config()

    def update_global(self):
        window = self.instance.activeWindow()
        if not window:
            return
        qwin = window.qwindow()
        if not self.dock_opts:
            self.dock_opts = qwin.dockOptions()

        # NOTE: This changes the default behaviour of Krita for all dockers!
        if script.cfg("alt_dock_behavior", bool):
            qwin.setDockOptions(
                QMainWindow.AnimatedDocks
                | QMainWindow.AllowTabbedDocks
                | QMainWindow.GroupedDragging
                | QMainWindow.AllowNestedDocks
                # | QMainWindow.VerticalTabs
            )
        else:
            qwin.setDockOptions(self.dock_opts)

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
        prepare_inpaint_action = window.createAction(
            "prepare_inpaint", "Add inpaint layer and switch brush", "tools/scripts"
        )
        prepare_inpaint_action.triggered.connect(lambda: script.action_prepare_inpaint())
        upscale_x_action = window.createAction(
            "img2img_inpaint", "Apply img2img inpaint", "tools/scripts"
        )
        upscale_x_action.triggered.connect(lambda: script.action_inpaint())
        simple_upscale_action = window.createAction(
            "simple_upscale", "Apply simple upscaler", "tools/scripts"
        )
        simple_upscale_action.triggered.connect(lambda: script.action_simple_upscale())
        interrupt_action = window.createAction(
            "paint_ext_interrupt", "Interrupt image generation", "tools/scripts"
        )
        interrupt_action.triggered.connect(lambda: script.action_interrupt())
