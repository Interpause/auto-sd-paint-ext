from functools import partial

from krita import QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ..defaults import DEFAULTS
from ..script import script
from ..widgets import QCheckBox, QLabel, QLineEditLayout


class ConfigTabWidget(QWidget):
    name = "config"

    def __init__(self, *args, **kwargs):
        super(ConfigTabWidget, self).__init__(*args, **kwargs)

        self.base_url = QLineEdit()
        self.base_url_reset = QPushButton("Default")
        inline1 = QHBoxLayout()
        inline1.addWidget(self.base_url)
        inline1.addWidget(self.base_url_reset)

        self.enc_key = QLineEditLayout(
            script.cfg, "encryption_key", "Optional Encryption Key"
        )

        # Plugin settings
        self.just_use_yaml = QCheckBox(
            script.cfg, "just_use_yaml", "(unrecommended) Ignore settings"
        )
        self.create_mask_layer = QCheckBox(
            script.cfg, "create_mask_layer", "Use selection as mask"
        )
        self.save_temp_images = QCheckBox(
            script.cfg, "save_temp_images", "Save images for debug"
        )
        self.fix_aspect_ratio = QCheckBox(
            script.cfg, "fix_aspect_ratio", "Adjust selection aspect ratio"
        )
        self.only_full_img_tiling = QCheckBox(
            script.cfg, "only_full_img_tiling", "Disallow tiling with selection"
        )
        self.include_grid = QCheckBox(
            script.cfg, "include_grid", "Include txt2img/img2img grid"
        )
        self.minimize_ui = QCheckBox(script.cfg, "minimize_ui", "Squeeze the UI")

        # webUI/backend settings
        self.filter_nsfw = QCheckBox(script.cfg, "filter_nsfw", "Filter NSFW")
        self.img2img_color_correct = QCheckBox(
            script.cfg, "img2img_color_correct", "Color correct img2img"
        )
        self.inpaint_color_correct = QCheckBox(
            script.cfg, "inpaint_color_correct", "Color correct inpaint"
        )
        self.do_exact_steps = QCheckBox(
            script.cfg,
            "do_exact_steps",
            "Exact number of steps for denoising",
        )

        self.refresh_btn = QPushButton("Auto-Refresh Options Now")
        self.restore_defaults = QPushButton("Restore Defaults")

        self.info_label = QLabel()
        self.info_label.setOpenExternalLinks(True)
        self.info_label.setWordWrap(True)

        # scroll_area = QScrollArea()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout_inner = QVBoxLayout()
        layout_inner.setContentsMargins(0, 0, 0, 0)

        layout_inner.addWidget(QLabel("<em>Plugin settings:</em>"))
        layout_inner.addWidget(self.minimize_ui)
        layout_inner.addWidget(self.create_mask_layer)
        layout_inner.addWidget(self.fix_aspect_ratio)
        layout_inner.addWidget(self.only_full_img_tiling)
        layout_inner.addWidget(self.include_grid)
        layout_inner.addWidget(self.save_temp_images)
        # layout_inner.addWidget(self.just_use_yaml)

        layout_inner.addWidget(QLabel("<em>Backend/webUI settings:</em>"))
        layout_inner.addWidget(self.filter_nsfw)
        layout_inner.addWidget(self.img2img_color_correct)
        layout_inner.addWidget(self.inpaint_color_correct)
        layout_inner.addWidget(self.do_exact_steps)

        # TODO: figure out how to set height of scroll area when there are too many options
        # or maybe an option search bar
        # scroll_area.setLayout(layout_inner)
        # scroll_area.setWidgetResizable(True)
        # layout.addWidget(scroll_area)
        layout.addWidget(QLabel("<em>Backend url:</em>"))
        layout.addLayout(inline1)
        layout.addLayout(self.enc_key)
        layout.addLayout(layout_inner)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.restore_defaults)
        layout.addWidget(self.info_label)
        layout.addStretch()

        self.setLayout(layout)

    def cfg_init(self):
        # NOTE: update timer -> cfg_init, setText seems to reset cursor position so we prevent it
        base_url = script.cfg("base_url", str)
        if self.base_url.text() != base_url:
            self.base_url.setText(base_url)

        self.enc_key.cfg_init()
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
        self.minimize_ui.cfg_init()

        info_text = """
            <em>Tip:</em> Only a selected few backend/webUI settings are exposed above.<br/>
            <em>Tip:</em> You should look through & configure all the backend/webUI settings at least once.
            <br/><br/>
            <a href="http://127.0.0.1:7860/" target="_blank">Configure all settings in webUI</a><br/>
            <a href="https://github.com/Interpause/auto-sd-paint-ext/wiki" target="_blank">Read the guide</a><br/>
            <a href="https://github.com/Interpause/auto-sd-paint-ext/issues" target="_blank">Report bugs or suggest features</a>
            """
        if script.cfg("minimize_ui", bool):
            info_text = "\n".join(info_text.split("\n")[-4:-1])
        self.info_label.setText(info_text)

    def cfg_connect(self):
        self.base_url.textChanged.connect(partial(script.cfg.set, "base_url"))
        # NOTE: this triggers on every keystroke; theres no focus lost signal...
        self.base_url.textChanged.connect(script.action_update_config)
        self.base_url_reset.released.connect(
            lambda: self.base_url.setText(DEFAULTS.base_url)
        )
        self.enc_key.cfg_connect()
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
        self.minimize_ui.cfg_connect()

        def restore_defaults():
            script.restore_defaults()
            # retrieve list of available stuff again
            script.action_update_config()

        self.refresh_btn.released.connect(script.action_update_config)
        self.restore_defaults.released.connect(restore_defaults)
        self.minimize_ui.toggled.connect(lambda _: script.config_updated.emit())
