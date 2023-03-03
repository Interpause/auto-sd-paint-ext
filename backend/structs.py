from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel

from .config import Img2ImgOptions, PluginOptions, Txt2ImgOptions, UpscaleOptions
from .utils import optional


@optional
class DefaultTxt2ImgOptions(Txt2ImgOptions):
    pass


class Txt2ImgRequest(DefaultTxt2ImgOptions):
    """Text2Img API request. If optional attributes aren't set, the defaults
    from `krita_config.yaml` will be used.
    """

    orig_width: int
    """Requested image width."""
    orig_height: int
    """Requested image height."""


@optional
class DefaultImg2ImgOptions(Img2ImgOptions):
    pass


class Img2ImgRequest(DefaultImg2ImgOptions):
    """Img2Img API request. If optional attributes aren't set, the defaults from
    `krita_config.yaml` will be used.
    """

    src_img: str
    """Image being used."""
    mask_img: Optional[str] = None
    """Image mask being used."""


@optional
class DefaultUpscaleOptions(UpscaleOptions):
    pass


class UpscaleRequest(DefaultUpscaleOptions):
    """Upscale API request. If optional attributes aren't set, the defaults from
    `krita_config.yaml` will be used.
    """

    src_img: str
    """Image being used."""


class ConfigResponse(PluginOptions):
    sample_path: str
    """Where the Krita plugin should save the selected region and mask."""
    upscalers: List[str]
    """List of available upscalers."""
    samplers: List[str]
    """List of available samplers."""
    samplers_img2img: List[str]
    """List of available samplers specifically for img2img (upstream separated them for a reason)."""
    scripts_txt2img: Dict[str, List[Dict]]
    """List of available txt2img scripts."""
    scripts_img2img: Dict[str, List[Dict]]
    """List of available img2img scripts."""
    face_restorers: List[str]
    """List of available face restorers."""
    sd_models: List[str]
    """List of available models."""
    sd_vaes: List[str]
    """List of available VAEs."""


class ImageResponse(BaseModel):
    outputs: List[str]
    """List of generated images encoded in base64."""
    info: str
    """Generation info already jsonified."""


class UpscaleResponse(BaseModel):
    output: str
    """Upscaled image in base64."""
