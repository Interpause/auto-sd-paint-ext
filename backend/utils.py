from __future__ import annotations

import inspect
import logging
import os
import secrets
from base64 import b64decode, b64encode
from io import BytesIO
from itertools import cycle
from math import ceil

import modules
import yaml
from modules import shared
from PIL import Image
from pydantic import BaseModel

from .config import CONFIG_PATH, ENCRYPT_FILE, LOGGER_NAME, MainConfig

log = logging.getLogger(LOGGER_NAME)


def load_config():
    """Load default config (including those not exposed in the API yet) from
    `CONFIG_PATH` in the current working directory.

    Will create `CONFIG_PATH` if it has yet to exist using `MainConfig` from
    `config.py`.

    Returns:
        MainConfig: config
    """
    if not os.path.isfile(CONFIG_PATH):
        cfg = MainConfig()
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(cfg.dict(), f)

    with open(CONFIG_PATH) as file:
        obj = yaml.safe_load(file)
        return MainConfig.parse_obj(obj)


def merge_default_config(config: BaseModel, default: BaseModel):
    """Replace unset and None fields in opt with values from default with the
    same field name in place.

    Unset fields does not include fields that are explicitly set to None but
    includes fields with a default value due to being unset.

    Args:
        config (BaseModel): Config object.
        default (BaseModel): Default to merge from.

    Returns:
        BaseModel: Modified config.
    """

    for field in config.__fields__:
        if not field in config.__fields_set__ or field is None:
            setattr(config, field, getattr(default, field, None))

    return config


def prepare_backend(opt: BaseModel):
    """Misc configuration and preparation tasks before calling internal API.

    Currently includes:
    - Ensuring the output/input folders exist
    - Set the global face restorer model to the selected one
    - Set the global SD model to the selected one
    - Set the global upscaler to the selected one
    - Set other misc global webUI/backend settings

    Args:
        opt (BaseModel): Option/Request object
    """
    # the `shared` module handles app state for the underlying codebase

    if hasattr(opt, "face_restorer"):
        shared.opts.face_restoration_model = opt.face_restorer
        shared.opts.code_former_weight = opt.codeformer_weight

    if hasattr(opt, "sd_model"):
        shared.opts.sd_model_checkpoint = opt.sd_model
        modules.sd_models.reload_model_weights(shared.sd_model)

    if hasattr(opt, "sd_vae"):
        shared.opts.sd_vae = opt.sd_vae
        modules.sd_vae.reload_vae_weights()

    if hasattr(opt, "upscaler_name"):
        shared.opts.upscaler_for_img2img = opt.upscaler_name

    if hasattr(opt, "color_correct"):
        shared.opts.img2img_color_correction = opt.color_correct
        shared.opts.img2img_fix_steps = opt.do_exact_steps

    if hasattr(opt, "filter_nsfw"):
        shared.opts.filter_nsfw = opt.filter_nsfw

    if hasattr(opt, "inpaint_mask_weight"):
        shared.opts.inpainting_mask_weight = opt.inpaint_mask_weight

    # Ensure the output/input folders exist
    if hasattr(opt, "sample_path"):
        os.makedirs(opt.sample_path, exist_ok=True)


def optional(*fields):
    """Decorator function used to modify a pydantic model's fields to all be optional.
    Alternatively, you can  also pass the field names that should be made optional as arguments
    to the decorator.
    Taken from https://github.com/samuelcolvin/pydantic/issues/1223#issuecomment-775363074
    """

    def dec(_cls):
        for field in fields:
            _cls.__fields__[field].required = False
        return _cls

    if fields and inspect.isclass(fields[0]) and issubclass(fields[0], BaseModel):
        cls = fields[0]
        fields = cls.__fields__
        return dec(cls)

    return dec


def save_img(image: Image.Image, sample_path: str, filename: str):
    """Saves an image.

    Args:
        image (Image): Image to save.
        sample_path (str): Folder to save the image in.
        filename (str): Name to save the image as.

    Returns:
        str: Absolute path where the image was saved.
    """
    path = os.path.join(sample_path, filename)
    image.save(path)
    return os.path.abspath(path)


def img_to_b64(image: Image.Image):
    """Convert an image to base64-encoded string.

    Args:
        image (Image): Image to encode.

    Returns:
        str: Base64-encoded image.
    """
    buf = BytesIO()
    image.save(buf, format="png")
    return b64encode(buf.getvalue()).decode("utf-8")


def b64_to_img(enc: str):
    """Convert base64-encoded string to image.

    Args:
        enc (str): Base64-encoded image.

    Returns:
        Image: Image.
    """
    return Image.open(BytesIO(b64decode(enc)))


def sddebz_highres_fix(
    base_size: int,
    max_size: int,
    orig_width: int,
    orig_height: int,
    just_stride=False,
    stride=8,
):
    """Calculate an appropiate image resolution given the base input size of the
    model and max input size allowed.

    The max input size is due to how Stable Diffusion currently handles resolutions
    larger than its base/native input size of 512, which can cause weird issues
    such as duplicated features in the image. Hence, it is typically better to
    render at a smaller appropiate resolution before using other methods to upscale
    to the original resolution. Setting max_size to 512, matching the base_size,
    imitates how the highres fix works.

    Stable Diffusion also messes up for resolutions smaller than 512. In which case,
    it is better to render at the base resolution before downscaling to the original.

    This method requires less user input than the builtin highres fix, which uses
    firstphase_width and firstphase_height.

    The original plugin writer, @sddebz, wrote this. I modified it to `ceil`
    instead of `round` to make selected region resizing easier in the plugin, and
    to avoid rounding to 0.

    Args:
        base_size (int): Native/base input size of the model.
        max_size (int): Max input size to accept.
        orig_width (int): Original width requested.
        orig_height (int): Original height requested.

    Returns:
        Tuple[int, int]: Appropiate (width, height) to use for the model.
    """

    def rnd(r, x):
        """Scale dimension x with stride z while attempting to preserve aspect ratio r."""
        return stride * ceil(r * x / stride)

    ratio = orig_width / orig_height

    # don't apply correction; just stride
    if just_stride:
        width, height = (
            ceil(orig_width / stride) * stride,
            ceil(orig_height / stride) * stride,
        )
    # height is smaller dimension
    elif orig_width > orig_height:
        width, height = rnd(ratio, base_size), base_size
        if width > max_size:
            width, height = max_size, rnd(1 / ratio, max_size)
    # width is smaller dimension
    else:
        width, height = base_size, rnd(1 / ratio, base_size)
        if height > max_size:
            width, height = rnd(ratio, max_size), max_size

    new_ratio = width / height

    log.info(
        f"img size: {orig_width}x{orig_height} -> {width}x{height}, "
        f"aspect ratio: {ratio:.2f} -> {new_ratio:.2f}, {100 * (new_ratio - ratio) / ratio :.2f}% change"
    )
    return width, height


def parse_prompt(val):
    """Parse different representations of prompt/negative prompt.

    Args:
        val (Any): Prompt to parse.

    Raises:
        SyntaxError: Value of the prompt key cannot be parsed.

    Returns:
        str: Correctly formatted prompt.
    """
    if val is None:
        return ""
    # Below cases are meant for prompts read from the yaml config
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return ", ".join(val)
    if isinstance(val, dict):
        prompt = ""
        for item, weight in val.items():
            if not prompt == "":
                prompt += " "
            if weight is None:
                prompt += f"{item}"
            else:
                prompt += f"({item}:{weight})"
        return prompt
    raise SyntaxError(f"prompt field in {CONFIG_PATH} is invalid")


def get_sampler_index(sampler_name: str):
    """Get index of sampler by name.

    Args:
        sampler_name (str): Exact name of sampler.

    Raises:
        KeyError: Sampler cannot be found.

    Returns:
        int: Index of sampler.
    """
    for index, sampler in enumerate(modules.sd_samplers.samplers):
        if sampler_name == sampler.name or sampler_name in sampler.aliases:
            return index
    raise KeyError(f"sampler not found: {sampler_name}")


def get_upscaler_index(upscaler_name: str):
    """Get index of upscaler by name.

    Args:
        upscaler_name (str): Exact name of upscaler.

    Raises:
        KeyError: Upscaler cannot be found.

    Returns:
        int: Index of sampler.
    """
    for index, upscaler in enumerate(shared.sd_upscalers):
        if upscaler.name == upscaler_name:
            return index
    raise KeyError(f"upscaler not found: {upscaler_name}")


def prepare_mask(mask: Image.Image):
    """Prepare mask for usage.

    Args:
        mask (Image): mask.

    Returns:
        Image: The luminance mask.
    """
    return mask.getchannel("A")


def bytewise_xor(msg: bytes, key: bytes):
    """Used for decrypting/encrypting request/response bodies."""
    return bytes(v ^ k for v, k in zip(msg, cycle(key)))


def get_encrypt_key():
    """Read encryption key from file."""
    try:
        with open(ENCRYPT_FILE) as f:
            return f.read().strip().encode("utf-8")
    except:
        if not os.path.exists(ENCRYPT_FILE):
            log.warning(
                f"Encryption key file doesn't exist at {os.path.abspath(ENCRYPT_FILE)}."
            )
            log.warning(f"Creating random encryption key.")
            with open(ENCRYPT_FILE, "w") as f:
                f.write(secrets.token_hex(16))
            log.warning(
                f"Key in {ENCRYPT_FILE} is completely optional. It can be used to encrypt messages between backend & Krita and is editable."
            )
            return get_encrypt_key()
    return None
