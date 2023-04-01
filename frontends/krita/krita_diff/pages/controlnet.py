from krita import QWidget, QVBoxLayout, QHBoxLayout, QStackedLayout

from ..script import script
from ..widgets import StatusBar, ImageLoaderLayout, QCheckBox, TipsLayout, QComboBoxLayout, QSpinBoxLayout

class ControlNetPage(QWidget):                                                      
    name = "ControlNet"

    def __init__(self, *args, **kwargs):
        super(ControlNetPage, self).__init__(*args, **kwargs)
        self.status_bar = StatusBar()
        self.controlnet_unit = QComboBoxLayout(
            script.cfg, "controlnet_unit_list", "controlnet_unit", label="Unit:"
        )
        self.controlnet_unit.qcombo.setEditable(False)
        self.controlnet_unit_layout_list = list(ControlNetUnitSettings(i) 
                                                for i in range(0, len(script.cfg("controlnet_unit_list"))))

        self.units_stacked_layout = QStackedLayout()
        
        for unit_layout in self.controlnet_unit_layout_list:
            self.units_stacked_layout.addWidget(unit_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.status_bar)
        layout.addLayout(self.controlnet_unit)
        layout.addLayout(self.units_stacked_layout)
        self.setLayout(layout)

    def controlnet_unit_changed(self, selected: str):
        self.units_stacked_layout.setCurrentIndex(int(selected)-1)

    def cfg_init(self):
        self.controlnet_unit.cfg_init()
        
        for controlnet_unit_layout in self.controlnet_unit_layout_list:
            controlnet_unit_layout.cfg_init()

    def cfg_connect(self):
        self.controlnet_unit.cfg_connect()

        for controlnet_unit_layout in self.controlnet_unit_layout_list:
            controlnet_unit_layout.cfg_connect()

        self.controlnet_unit.qcombo.currentTextChanged.connect(self.controlnet_unit_changed)
        script.status_changed.connect(lambda s: self.status_bar.set_status(s))

class ControlNetUnitSettings(QWidget):    
    def __init__(self, cfg_unit_number: int = 0, *args, **kwargs):
        super(ControlNetUnitSettings, self).__init__(*args, **kwargs)

        #Top checkbox
        self.enable = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_enable", f"Enable ControlNet {cfg_unit_number}"
        )
        self.use_selection_as_input = QCheckBox(
            script.cfg, f"controlnet{cfg_unit_number}_use_selection_as_input", "Use selection as input"
        )

        self.image_loader = ImageLoaderLayout()

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
            script.cfg, "controlnet_preprocessor_list", f"controlnet{cfg_unit_number}_preprocessor", label="Preprocessor:"
        )

        #Model list
        self.model_layout = QComboBoxLayout(
            script.cfg, "controlnet_model_list", f"controlnet{cfg_unit_number}_model", label="Model:"
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

        #Preprocessor settings
        self.annotator_resolution = QSpinBoxLayout(
            script.cfg, 
            f"controlnet{cfg_unit_number}_preprocessor_resolution", 
            label="Preprocessor resolution:", 
            min=64, 
            max=2048, 
            step=1
        )
        self.treshold_a = QSpinBoxLayout(
            script.cfg,
            f"controlnet{cfg_unit_number}_treshold_a",
            label="Treshold A:",
            min=1,
            max=255,
            step=1
        )
        self.treshold_b = QSpinBoxLayout(
            script.cfg,
            f"controlnet{cfg_unit_number}_treshold_b",
            label="Treshold B:",
            min=1,
            max=255,
            step=1
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

        preprocessor_settings_layout = QHBoxLayout()
        preprocessor_settings_layout.addLayout(self.annotator_resolution)
        preprocessor_settings_layout.addLayout(self.treshold_a)
        preprocessor_settings_layout.addLayout(self.treshold_b)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_checkbox_layout)
        layout.addLayout(self.image_loader)
        layout.addLayout(self.tips)
        layout.addLayout(main_settings_layout)
        layout.addLayout(self.preprocessor_layout)
        layout.addLayout(self.model_layout)
        layout.addLayout(guidance_layout)
        layout.addLayout(preprocessor_settings_layout)
        layout.addStretch()

        self.setLayout(layout)

    def change_image_loader_state(self, state):
        if state == 1 or state == 2:
            self.image_loader.disable()
        else:
            self.image_loader.enable()

    def preprocessor_changed(self, selected: str):
        self.init_preprocessor_layouts(selected)
        if selected in preprocessor_settings:
            self.annotator_resolution.label = preprocessor_settings[selected]["resolution_label"] \
                if "resolution_label" in preprocessor_settings[selected] else "Preprocessor resolution:"
            
            if "treshold_a_label" in preprocessor_settings[selected]:
                self.treshold_a.label = preprocessor_settings[selected]["treshold_a_label"]
                self.treshold_a.min = preprocessor_settings[selected]["treshold_a_min_value"] \
                    if "treshold_a_min_value" in preprocessor_settings[selected] else 0
                self.treshold_a.max = preprocessor_settings[selected]["treshold_a_max_value"] \
                    if "treshold_a_max_value" in preprocessor_settings[selected] else 0
                self.treshold_a.value = preprocessor_settings[selected]["treshold_a_value"] \
                    if "treshold_a_value" in preprocessor_settings[selected] else 0
                self.treshold_a.step = preprocessor_settings[selected]["treshold_step"] \
                    if "treshold_step" in preprocessor_settings[selected] else 1
            else:
                self.treshold_a.hide()
            
            if "treshold_b_label" in preprocessor_settings[selected]:
                self.treshold_b.label = preprocessor_settings[selected]["treshold_b_label"]
                self.treshold_b.min = preprocessor_settings[selected]["treshold_b_min_value"] \
                    if "treshold_b_min_value" in preprocessor_settings[selected] else 0
                self.treshold_b.max = preprocessor_settings[selected]["treshold_b_max_value"] \
                    if "treshold_b_max_value" in preprocessor_settings[selected] else 0
                self.treshold_b.value = preprocessor_settings[selected]["treshold_b_value"] \
                    if "treshold_b_value" in preprocessor_settings[selected] else 0
                self.treshold_b.step = preprocessor_settings[selected]["treshold_step"] \
                    if "treshold_step" in preprocessor_settings[selected] else 1
    
    def init_preprocessor_layouts(self, selected: str):
        if selected in preprocessor_settings:
            self.show_preprocessor_options()
        else:
            self.hide_preprocessor_options()
    
    def hide_preprocessor_options(self):
        self.annotator_resolution.qlabel.hide()
        self.annotator_resolution.qspin.hide()
        self.treshold_a.qlabel.hide()
        self.treshold_a.qspin.hide()
        self.treshold_b.qlabel.hide()
        self.treshold_b.qspin.hide()

    def show_preprocessor_options(self):
        self.annotator_resolution.qlabel.show()
        self.annotator_resolution.qspin.show()
        self.treshold_a.qlabel.show()
        self.treshold_a.qspin.show()
        self.treshold_b.qlabel.show()
        self.treshold_b.qspin.show()

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
        self.change_image_loader_state(self.use_selection_as_input.checkState())
        self.init_preprocessor_layouts(self.preprocessor_layout.qcombo.currentText())

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
        self.preprocessor_layout.qcombo.currentTextChanged.connect(self.preprocessor_changed)

preprocessor_settings = {
    "canny": {
        "resolution_label": "Annotator resolution",
        "treshold_a_label": "Canny low treshold",
        "treshold_b_label": "Canny high treshold",
        "treshold_a_value": 100,
        "treshold_b_value": 200,
        "treshold_a_min_value": 1,
        "treshold_a_max_value": 255,
        "treshold_b_min_value": 1,
        "treshold_b_max_value": 255
    },
    "depth": {
        "resolution_label": "Midas resolution",
    },
    "depth_leres": {
        "resolution_label": "LeReS resolution",
        "treshold_a_label": "Remove near %",
        "treshold_b_label": "Remove background %",
        "treshold_a_min_value": 0,
        "treshold_a_max_value": 100,
        "treshold_b_min_value": 0,
        "treshold_b_max_value": 100
    },
    "hed": {
        "resolution_label": "HED resolution",
    },
    "mlsd": {
        "resolution_label": "Hough resolution",
        "treshold_a_label": "Hough value threshold (MLSD)",
        "treshold_b_label": "Hough distance threshold (MLSD)",
        "treshold_a_value": 0.1,
        "treshold_b_value": 0.1,
        "treshold_a_min_value": 0.01,
        "treshold_b_max_value": 2,
        "treshold_a_min_value": 0.01,
        "treshold_b_max_value": 20,
        "treshold_step": 0.01
    },
    "normal_map": {
        "treshold_a_label": "Normal background threshold",
        "treshold_a_value": 0.4,
        "treshold_a_min_value": 0,
        "treshold_a_max_value": 1,
        "treshold_b_min_value": 0,
        "treshold_b_max_value": 1,
        "treshold_step": 0.01
    },
    "openpose": {},
    "openpose_hand": {},
    "clip_vision": {},
    "color": {},
    "pidinet": {},
    "scribble": {},
    "fake_scribble": {
        "resolution_label": "HED resolution",
    },
    "segmentation": {},
    "binary": {
        "treshold_a_label": "Binary threshold",
        "treshold_a_min_value": 0,
        "treshold_a_max_value": 255,
        "treshold_b_min_value": 0,
        "treshold_b_max_value": 255,
    }
}