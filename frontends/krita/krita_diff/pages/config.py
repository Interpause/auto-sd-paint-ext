from functools import partial

from krita import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ..defaults import DEFAULTS
from ..script import script
from ..widgets import QCheckBox, QLabel


class ConfigTabWidget(QWidget):
    def __init__(self, update_func, *args, **kwargs):
        super(ConfigTabWidget, self).__init__(*args, **kwargs)

        # callback to update all the other widgets
        self.update_func = update_func

        self.base_url = QLineEdit()
        self.base_url_reset = QPushButton("Default")
        inline1 = QHBoxLayout()
        inline1.addWidget(self.base_url)
        inline1.addWidget(self.base_url_reset)

        # Plugin settings
        self.just_use_yaml = QCheckBox(
            script.cfg,
            "just_use_yaml",
            "Override with krita_config.yaml (unrecommended)",
        )
        self.create_mask_layer = QCheckBox(
            script.cfg, "create_mask_layer", "Create transparency mask from selection"
        )
        self.save_temp_images = QCheckBox(
            script.cfg, "save_temp_images", "Save images sent to/from backend for debug"
        )
        self.fix_aspect_ratio = QCheckBox(
            script.cfg, "fix_aspect_ratio", "Fix aspect ratio for selections"
        )
        self.only_full_img_tiling = QCheckBox(
            script.cfg, "only_full_img_tiling", "Only allow tiling with no selection"
        )
        self.include_grid = QCheckBox(
            script.cfg, "include_grid", "Include grid for txt2img and img2img"
        )

        # webUI/backend settings
        self.filter_nsfw = QCheckBox(script.cfg, "filter_nsfw", "Filter NSFW content")
        self.img2img_color_correct = QCheckBox(
            script.cfg,
            "img2img_color_correct",
            "Color correct img2img for better blending",
        )
        self.inpaint_color_correct = QCheckBox(
            script.cfg,
            "inpaint_color_correct",
            "Color correct inpaint for better blending",
        )
        self.do_exact_steps = QCheckBox(
            script.cfg,
            "do_exact_steps",
            "Don't decrease steps based on denoising strength",
        )

        self.refresh_btn = QPushButton("Auto-Refresh Options Now")
        self.restore_defaults = QPushButton("Restore Defaults")

        info_label = QLabel(
            """
            <em>Tip:</em> Only a selected few backend/webUI settings are exposed above.<br/>
            <em>Tip:</em> You should look through & configure all the backend/webUI settings at least once.
            <br/><br/>
            <a href="http://127.0.0.1:7860/" target="_blank">Configure all settings in webUI</a><br/>
            <a href="https://github.com/Interpause/auto-sd-paint-ext/wiki" target="_blank">Read the guide</a><br/>
            <a href="https://github.com/Interpause/auto-sd-paint-ext/issues" target="_blank">Report bugs or suggest features</a>
            """
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("<em>Backend url:</em>"))
        layout.addLayout(inline1)

        layout.addWidget(QLabel("<em>Plugin settings:</em>"))
        layout.addWidget(self.just_use_yaml)
        layout.addWidget(self.create_mask_layer)
        layout.addWidget(self.save_temp_images)
        layout.addWidget(self.fix_aspect_ratio)
        layout.addWidget(self.only_full_img_tiling)
        layout.addWidget(self.include_grid)

        layout.addWidget(QLabel("<em>Backend/webUI settings:</em>"))
        layout.addWidget(self.filter_nsfw)
        layout.addWidget(self.img2img_color_correct)
        layout.addWidget(self.inpaint_color_correct)
        layout.addWidget(self.do_exact_steps)
        layout.addStretch()
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.restore_defaults)
        layout.addWidget(info_label)

        self.setLayout(layout)

    def cfg_init(self):
        # NOTE: update timer -> cfg_init, setText seems to reset cursor position so we prevent it
        base_url = script.cfg("base_url", str)
        if self.base_url.text() != base_url:
            self.base_url.setText(base_url)

        self.just_use_yaml.cfg_init()
        self.create_mask_layer.cfg_init()
        self.save_temp_images.cfg_init()
        self.fix_aspect_ratio.cfg_init()
        self.only_full_img_tiling.cfg_init()
        self.include_grid.cfg_init()
        self.filter_nsfw.cfg_init()
        self.img2img_color_correct.cfg_init()
        self.inpaint_color_correct.cfg_init()
        self.do_exact_steps.cfg_init()

    def cfg_connect(self):
        self.base_url.textChanged.connect(partial(script.cfg.set, "base_url"))
        # NOTE: this triggers on every keystroke; theres no focus lost signal...
        self.base_url.textChanged.connect(script.update_config)
        self.base_url_reset.released.connect(
            lambda: self.base_url.setText(DEFAULTS.base_url)
        )
        self.just_use_yaml.cfg_connect()
        self.create_mask_layer.cfg_connect()
        self.save_temp_images.cfg_connect()
        self.fix_aspect_ratio.cfg_connect()
        self.only_full_img_tiling.cfg_connect()
        self.include_grid.cfg_connect()
        self.filter_nsfw.cfg_connect()
        self.img2img_color_correct.cfg_connect()
        self.inpaint_color_correct.cfg_connect()
        self.do_exact_steps.cfg_connect()

        def update_remote_config():
            script.update_config()
            self.update_func()

        def restore_defaults():
            script.restore_defaults()
            # retrieve list of available stuff again
            script.update_config()
            self.update_func()

        self.refresh_btn.released.connect(update_remote_config)
        self.restore_defaults.released.connect(restore_defaults)
