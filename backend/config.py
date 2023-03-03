from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

SCRIPT_NAME = "Interpause Backend API"
SCRIPT_ID = "interpause_backend_api"
ROUTE_PREFIX = "/sdapi/interpause"
CONFIG_PATH = "auto-sd-paint-ext-backend.yaml"
LOGGER_NAME = "auto-sd-paint-ext"
ENCRYPT_FILE = "xor_pass.txt"

# names of scripts to apply workarounds for
NAME_SCRIPT_LOOPBACK = "Loopback"
NAME_SCRIPT_UPSCALE = "SD upscale"


class BaseOptions(BaseModel):
    sample_path: str = "outputs/krita-out"
    """Where to save generated images to."""
    save_samples: bool = False
    """Whether to save temporary images (useful for debugging)."""


class GenerationOptions(BaseModel):
    sd_model: str = "model.ckpt"
    """Model to use for generation."""
    sd_vae: str = "Automatic"
    """VAE to use for generation."""

    clip_skip: int = 1
    """CLIP layers to skip during generation."""

    script: str = "None"
    """Which script to use."""
    script_args: list = Field(default_factory=list)
    """List of args for script."""

    prompt: Any = "dog"
    """Requested prompt."""
    negative_prompt: Any = ""
    """Requested negative prompt."""
    seed: int = -1
    """Seed used for noise generation. Incremented by 1 for each image rendered."""

    seed_enable_extras: bool = False
    """Enable subseed variation."""
    subseed: int = -1
    """Subseed to use for subseed variation. Incremented by 1 for each image rendered."""
    subseed_strength: float = 0.0
    """Strength of subseed compared to seed. 0.0 will be completely original seed, 1.0 will be completely subseed."""
    seed_resize_from_h: int = 0
    """Original resolution seed was used at. Used to resize latent noise to attempt to generate same image with a different resolution."""
    seed_resize_from_w: int = 0
    """Original resolution seed was used at. Used to resize latent noise to attempt to generate same image with a different resolution."""

    sampler_name: str = "Euler a"
    """Exact name of sampler to use. Name should follow exact spelling and capitalization as in the WebUI."""
    steps: int = 30
    """Number of steps for diffusion."""
    cfg_scale: float = 7.5
    """Guidance scale for diffusion."""
    denoising_strength: float = 0.35
    """Strength of denoising from 0.0 to 1.0."""

    batch_count: int = 1
    """Number of batches to render."""
    batch_size: int = 1
    """Number of images per batch to render."""

    base_size: int = 512
    """Native/base resolution of model used."""
    max_size: int = 768
    """Max input resolution allowed to prevent image artifacts."""
    disable_sddebz_highres: bool = False
    """Disable base size/max size system above."""
    tiling: bool = False
    """Whether to generate a tileable image."""
    highres_fix: bool = False
    """Whether to enable workaround for higher resolution at cost of time."""
    firstphase_height: int = 512
    """Max height for first phase of highres fix (before upscaling to requested resolution)."""
    firstphase_width: int = 512
    """Max width for first phase of highres fix (before upscaling to requested resolution)."""

    # upscale_overlap: int = 64
    # """Size of overlap in pixels for upscaling.""" Configure this in WebUI
    upscaler_name: str = "None"
    """Exact name of upscaler to use."""
    filter_nsfw: bool = False
    """filter NSFW content."""

    include_grid: bool = False
    """Whether to include the image grid in the results sent to Krita"""


class SamplerParamOptions(BaseModel):
    # TODO: More conveniently expose config options for samplers/explain them.
    pass


class FaceRestorationOptions(BaseModel):
    restore_faces: bool = False
    """Whether to use GFPGAN for face restoration."""
    face_restorer: str = "CodeFormer"
    """Exact name of face restorer to use."""
    codeformer_weight: float = 0.5
    """Strength of face restoration if using CodeFormer. 0.0 is the strongest and 1.0 is the weakest."""


class InpaintingOptions(BaseModel):
    inpainting_fill: int = 1
    """What to fill inpainted region with. 0 is blur/fill, 1 is original, 2 is latent noise, and 3 is latent empty."""
    inpaint_full_res: bool = False
    """(DISABLED) Whether to use the full resolution for inpainting."""
    inpaint_full_res_padding: int = 0
    """(DISABLED) Padding when using full resolution for inpainting."""
    mask_blur: int = 0
    """(DISABLED) Size of blur at boundaries of mask."""
    invert_mask: bool = False
    """Whether to invert the mask."""
    inpaint_mask_weight: float = 1.0
    """Mask weight for specialized inpainting models."""


class Txt2ImgOptions(BaseOptions, GenerationOptions, FaceRestorationOptions):
    pass


class Img2ImgOptions(
    BaseOptions, GenerationOptions, InpaintingOptions, FaceRestorationOptions
):
    is_inpaint: bool = False
    """Img2Img mode"""
    resize_mode: int = 1
    """Unused by Krita plugin since rescaling is done by us. 0 is stretch to fit, 1 is cover, 2 is contain."""

    steps: int = 50

    color_correct: bool = True
    """Apply color correction after img2img/inpaint to match original & blend better."""
    do_exact_steps: bool = True
    """Do exactly the number of steps specified by the slider instead of less during img2img/inpaint."""


class UpscaleOptions(BaseOptions):
    upscaler_name: str = "None"
    """Exact name of upscaler to use."""
    downscale_first: bool = False
    """Whether to downscale the image by x0.5 first."""


class PluginOptions(BaseOptions):
    sample_path: str = "outputs/krita-in"


class MainConfig(BaseModel):
    txt2img: Txt2ImgOptions = Txt2ImgOptions()
    img2img: Img2ImgOptions = Img2ImgOptions()
    upscale: UpscaleOptions = UpscaleOptions()
    plugin: PluginOptions = PluginOptions()
