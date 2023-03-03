from dataclasses import dataclass, field
from typing import List

# set combo box to error msg instead of blank when cannot retrieve options from backend
ERROR_MSG = "Retrieval Failed"

# Used for status bar
STATE_READY = "Ready"
STATE_INIT = "Errors will be shown here"
STATE_URLERROR = "Network error"
STATE_RESET_DEFAULT = "All settings reset"
STATE_WAIT = "Please wait..."
STATE_DONE = "Done!"
STATE_INTERRUPT = "Interrupted!"

# Other currently hardcoded stuff
SHORT_TIMEOUT = 10
LONG_TIMEOUT = None  # requests that might take "forever", i.e., image generation with high batch count
REFRESH_INTERVAL = 3000  # 3 seconds between auto-config refresh
ETA_REFRESH_INTERVAL = 250  # milliseconds between eta refresh
CFG_FOLDER = "krita"  # which folder in ~/.config to store config
CFG_NAME = "krita_diff_plugin"  # name of config file
EXT_CFG_NAME = "krita_diff_plugin_scripts"  # name of config file
ADD_MASK_TIMEOUT = 50
THREADED = True
ROUTE_PREFIX = "/sdapi/interpause/"
OFFICIAL_ROUTE_PREFIX = "/sdapi/v1/"

# error messages
ERR_MISSING_CONFIG = "Report this bug, developer missed out a config key somewhere."
ERR_NO_DOCUMENT = "No document open yet!"
ERR_NO_CONNECTION = "Cannot reach backend!"
ERR_BAD_URL = "Invalid backend URL!"

# tab IDs
TAB_SDCOMMON = "krita_diff_sdcommon"
TAB_CONFIG = "krita_diff_config"
TAB_TXT2IMG = "krita_diff_txt2img"
TAB_IMG2IMG = "krita_diff_img2img"
TAB_INPAINT = "krita_diff_inpaint"
TAB_UPSCALE = "krita_diff_upscale"
TAB_PREVIEW = "krita_diff_preview"


@dataclass(frozen=True)
class Defaults:
    base_url: str = "http://127.0.0.1:7860"
    encryption_key: str = ""
    just_use_yaml: bool = False
    create_mask_layer: bool = True
    save_temp_images: bool = False
    fix_aspect_ratio: bool = True
    only_full_img_tiling: bool = True
    filter_nsfw: bool = False
    do_exact_steps: bool = True
    sample_path: str = "."
    minimize_ui: bool = False
    first_setup: bool = True  # only used for the initial docker layout
    alt_dock_behavior: bool = False
    hide_layers: bool = True
    no_groups: bool = False
    disable_sddebz_highres: bool = False

    sd_model_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    sd_model: str = "model.ckpt"
    sd_vae_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    sd_vae: str = "Automatic"
    clip_skip: int = 1
    sd_batch_size: int = 1
    sd_batch_count: int = 1
    sd_base_size: int = 512
    sd_max_size: int = 768
    sd_tiling: bool = False
    upscaler_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    upscaler_name: str = "None"
    face_restorer_model_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    face_restorer_model: str = "None"
    codeformer_weight: float = 0.5
    include_grid: bool = False

    txt2img_prompt: str = ""
    txt2img_negative_prompt: str = ""
    txt2img_sampler_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    txt2img_sampler: str = "Euler a"
    txt2img_steps: int = 20
    txt2img_cfg_scale: float = 7.0
    txt2img_denoising_strength: float = 0.7
    txt2img_seed: str = ""
    txt2img_highres: bool = False
    txt2img_script: str = "None"
    txt2img_script_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    # TODO: Seed variation

    img2img_prompt: str = ""
    img2img_negative_prompt: str = ""
    img2img_sampler_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    img2img_sampler: str = "Euler a"
    img2img_steps: int = 40
    img2img_cfg_scale: float = 12.0
    img2img_denoising_strength: float = 0.8
    img2img_seed: str = ""
    img2img_color_correct: bool = False
    img2img_script: str = "None"
    img2img_script_list: List[str] = field(default_factory=lambda: [ERROR_MSG])

    inpaint_prompt: str = ""
    inpaint_negative_prompt: str = ""
    inpaint_sampler_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    inpaint_sampler: str = "LMS"
    inpaint_steps: int = 100
    inpaint_cfg_scale: float = 5.0
    inpaint_denoising_strength: float = 0.40
    inpaint_seed: str = ""
    inpaint_invert_mask: bool = False
    # inpaint_mask_blur: int = 4
    inpaint_fill_list: List[str] = field(
        # NOTE: list order corresponds to number to use in internal API!!!
        default_factory=lambda: ["blur", "preserve", "latent noise", "latent empty"]
    )
    inpaint_fill: str = "preserve"
    # inpaint_full_res: bool = False
    # inpaint_full_res_padding: int = 32
    inpaint_color_correct: bool = False
    inpaint_script: str = "None"
    inpaint_script_list: List[str] = field(default_factory=lambda: [ERROR_MSG])
    inpaint_mask_weight: float = 1.0

    upscale_upscaler_name: str = "None"
    upscale_downscale_first: bool = False


DEFAULTS = Defaults()
