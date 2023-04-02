from krita import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QStackedLayout

from ..defaults import CONTROLNET_PREPROCESSOR_SETTINGS
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
                                                for i in range(len(script.cfg("controlnet_unit_list"))))

        self.units_stacked_layout = QStackedLayout()
        
        for unit_layout in self.controlnet_unit_layout_list:
            self.units_stacked_layout.addWidget(unit_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.status_bar)
        layout.addLayout(self.controlnet_unit)
        layout.addLayout(self.units_stacked_layout)
        self.setLayout(layout)

    def controlnet_unit_changed(self, selected: str):
        self.units_stacked_layout.setCurrentIndex(int(selected))

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

        #Refresh button
        self.refresh_button = QPushButton("Refresh")

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
        guidance_layout.addLayout(self.guidance_start_layout)
        guidance_layout.addLayout(self.guidance_end_layout)

        treshold_layout = QHBoxLayout()
        treshold_layout.addLayout(self.treshold_a)
        treshold_layout.addLayout(self.treshold_b)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_checkbox_layout)
        layout.addLayout(self.image_loader)
        layout.addLayout(self.tips)
        layout.addLayout(main_settings_layout)
        layout.addLayout(self.preprocessor_layout)
        layout.addLayout(self.model_layout)
        layout.addWidget(self.refresh_button)
        layout.addLayout(self.weight_layout)
        layout.addLayout(guidance_layout)
        layout.addLayout(self.annotator_resolution)
        layout.addLayout(treshold_layout)
        layout.addStretch()

        self.setLayout(layout)

    def change_image_loader_state(self, state):
        if state == 1 or state == 2:
            self.image_loader.disable()
        else:
            self.image_loader.enable()

    def set_preprocessor_options(self, selected: str):
        if selected in CONTROLNET_PREPROCESSOR_SETTINGS:
            self.show_preprocessor_options()
            self.annotator_resolution.qlabel.setText(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["resolution_label"] \
                if "resolution_label" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else "Preprocessor resolution:")
            
            if "treshold_a_label" in CONTROLNET_PREPROCESSOR_SETTINGS[selected]:
                self.treshold_a.qlabel.show()
                self.treshold_a.qspin.show()
                self.treshold_a.qlabel.setText(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_a_label"])
                self.treshold_a.qspin.setMinimum(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_a_min_value"] \
                    if "treshold_a_min_value" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else 0)
                self.treshold_a.qspin.setMaximum(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_a_max_value"] \
                    if "treshold_a_max_value" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else 0)
                self.treshold_a.qspin.setValue(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_a_value"] \
                    if "treshold_a_value" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else self.treshold_a.qspin.minimum())
                self.treshold_a.qspin.setSingleStep(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_step"] \
                    if "treshold_step" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else 1)
            else:
                self.treshold_a.qlabel.hide()
                self.treshold_a.qspin.hide()
            
            if "treshold_b_label" in CONTROLNET_PREPROCESSOR_SETTINGS[selected]:
                self.treshold_b.qlabel.show()
                self.treshold_b.qspin.show()
                self.treshold_b.qlabel.setText(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_b_label"])
                self.treshold_b.qspin.setMinimum(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_b_min_value"] \
                    if "treshold_b_min_value" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else 0)
                self.treshold_b.qspin.setMaximum(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_b_max_value"] \
                    if "treshold_b_max_value" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else 0)
                self.treshold_b.qspin.setValue(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_b_value"] \
                    if "treshold_b_value" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else self.treshold_b.qspin.minimum())
                self.treshold_b.qspin.setSingleStep(CONTROLNET_PREPROCESSOR_SETTINGS[selected]["treshold_b_step"] \
                    if "treshold_b_step" in CONTROLNET_PREPROCESSOR_SETTINGS[selected] else 1)
            else:
                self.treshold_b.qlabel.hide()
                self.treshold_b.qspin.hide()
        else:
            self.hide_preprocessor_options(selected)
    
    def hide_preprocessor_options(self, selected: str):
        if selected == "none":
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

    def enabled_changed(self, state):
        if state == 1 or state == 2:
            script.action_update_controlnet_config()

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
        self.annotator_resolution.cfg_init()
        self.treshold_a.cfg_init()
        self.treshold_b.cfg_init()
        self.change_image_loader_state(self.use_selection_as_input.checkState())
        self.set_preprocessor_options(self.preprocessor_layout.qcombo.currentText())

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
        self.annotator_resolution.cfg_connect()
        self.treshold_a.cfg_connect()
        self.treshold_b.cfg_connect()
        self.enable.stateChanged.connect(self.enabled_changed)
        self.use_selection_as_input.stateChanged.connect(self.change_image_loader_state)
        self.preprocessor_layout.qcombo.currentTextChanged.connect(self.set_preprocessor_options)
        self.refresh_button.released.connect(lambda: script.action_update_controlnet_config())