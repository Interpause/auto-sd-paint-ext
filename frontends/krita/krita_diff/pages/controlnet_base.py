from krita import QWidget, QVBoxLayout, QHBoxLayout

from ..script import script
from ..widgets import StatusBar, ImageLoader, QCheckBox, TipsLayout, QComboBoxLayout, QSpinBoxLayout

class ControlNetPageBase(QWidget):
    name = "ControlNet"

    def __init__(self, cfg_unit_number: int = 0, *args, **kwargs):
        super(ControlNetPageBase, self).__init__(*args, **kwargs)
        self.status_bar = StatusBar()

        #Top checkbox
        self.enable = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_enable", "Enable ControlNet"
        )
        self.use_selection_as_input = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_use_selection_as_input", "Use selection as input"
        )

        self.image_loader = ImageLoader()

        #Main settings
        self.invert_input_color = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_invert_input_color", "Invert input color"
        )
        self.RGB_to_BGR = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_RGB_to_BGR", "RGB to BGR"
        )
        self.low_vram = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_low_vram", "Low VRAM"
        )
        self.guess_mode = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_guess_mode", "Guess mode"
        )

        #Tips
        self.tips = TipsLayout(
            ["Invert colors if your image has white background."]
        )

        #Preprocessor list
        self.preprocessor_layout = QComboBoxLayout(
            script.cfg, 
            f"controlnet{cfg_unit_number}_preprocessor_list", 
            f"controlnet{cfg_unit_number}_preprocessor", 
            label="Preprocessor:"
        )

        #Model list
        self.model_layout = QComboBoxLayout(
            script.cfg, f"controlnet{cfg_unit_number}_model_list", f"controlnet{cfg_unit_number}_model", label="Model:"
        )

        self.weight_layout = QSpinBoxLayout(
            script.cfg, f"controlnet{cfg_unit_number}_weight", label="Weight:", min=0, max=2, step=0.05
        )

        self.guidance_start_layout = QSpinBoxLayout(
            script.cfg, f"controlnet{cfg_unit_number}_guidance_start", label="Guidance start:", min=0, max=1, step=0.01
        )

        self.guidance_end_layout = QSpinBoxLayout(
            script.cfg, f"controlnet{cfg_unit_number}_guidance_end", label="Guidance end:", min=0, max=1, step=0.01
        )

        top_checkbox_layout = QHBoxLayout()
        top_checkbox_layout.addWidget(self.enable)
        top_checkbox_layout.addWidget(self.use_selection_as_input)

        main_settings_layout = QHBoxLayout()
        main_settings_layout.addWidget(self.invert_input_color)
        main_settings_layout.addWidget(self.RGB_to_BGR)
        main_settings_layout.addWidget(self.low_vram)
        main_settings_layout.addWidget(self.guess_mode)

        guidance_layout = QHBoxLayout()
        guidance_layout.addLayout(self.weight_layout)
        guidance_layout.addLayout(self.guidance_start_layout)
        guidance_layout.addLayout(self.guidance_end_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.status_bar)
        layout.addLayout(top_checkbox_layout)
        layout.addWidget(self.image_loader)
        layout.addLayout(self.tips)
        layout.addLayout(main_settings_layout)
        layout.addLayout(self.preprocessor_layout)
        layout.addLayout(self.model_layout)
        layout.addLayout(guidance_layout)
        layout.addStretch()
        self.setLayout(layout)

    def change_image_loader_state(self, state):
        if state == 1 or state == 2:
            self.image_loader.setEnabled(False)
        else:
            self.image_loader.setEnabled(True)

    def cfg_init(self):  
        self.enable.cfg_init()
        self.use_selection_as_input.cfg_init()
        self.invert_input_color.cfg_init()
        self.RGB_to_BGR.cfg_init()
        self.low_vram.cfg_init()
        self.guess_mode.cfg_init()
        self.preprocessor_layout.cfg_init()
        self.model_layout.cfg_init()
        self.weight_layout.cfg_init()
        self.guidance_start_layout.cfg_init()
        self.guidance_end_layout.cfg_init()
        self.tips.setVisible(not script.cfg("minimize_ui", bool))
        self.change_image_loader_state(self.use_selection_as_input.checkState())

    def cfg_connect(self):
        self.enable.cfg_connect()
        self.use_selection_as_input.cfg_connect()
        self.invert_input_color.cfg_connect()
        self.RGB_to_BGR.cfg_connect()
        self.low_vram.cfg_connect()
        self.guess_mode.cfg_connect()
        self.preprocessor_layout.cfg_connect()
        self.model_layout.cfg_connect()
        self.weight_layout.cfg_connect()
        self.guidance_start_layout.cfg_connect()
        self.guidance_end_layout.cfg_connect()
        self.use_selection_as_input.stateChanged.connect(self.change_image_loader_state)
        script.status_changed.connect(lambda s: self.status_bar.set_status(s))