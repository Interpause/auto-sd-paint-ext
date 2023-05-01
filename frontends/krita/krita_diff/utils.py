import json
import re
from itertools import cycle
from math import ceil

from krita import Krita, QBuffer, QByteArray, QImage, QColor, QIODevice, Qt

from .config import Config
from .defaults import (
    TAB_CONFIG,
    TAB_IMG2IMG,
    TAB_INPAINT,
    TAB_PREVIEW,
    TAB_SDCOMMON,
    TAB_TXT2IMG,
    TAB_UPSCALE,
    TAB_CONTROLNET
)


def fix_prompt(prompt: str):
    """Replace empty prompts with None."""
    return prompt if prompt != "" else None


def get_ext_key(ext_type: str, ext_name: str, index: int = None):
    """Get name of config key where the ext values would be stored."""
    return "_".join(
        [
            ext_type,
            re.sub(r"\W+", "", ext_name.lower()),
            "meta" if index is None else str(index),
        ]
    )


def get_ext_args(ext_cfg: Config, ext_type: str, ext_name: str):
    """Get args for script in positional list form."""
    raw = ext_cfg(get_ext_key(ext_type, ext_name))
    meta = []
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Invalid metadata: {raw}")
    args = []
    for i, o in enumerate(meta):
        typ = type(o["val"])
        if issubclass(typ, list):
            typ = "QStringList"
        val = ext_cfg(get_ext_key(ext_type, ext_name, i), typ)
        args.append(val)
    return args

def calculate_resized_image_dimensions(
        base_size: int, max_size: int, orig_width: int, orig_height: int
):
    """Finds the dimensions of the resized images based on base_size and max_size.
    See https://github.com/Interpause/auto-sd-paint-ext#faq for more details."""

    def rnd(r, x, z=64):
        """Scale dimension x with stride z while attempting to preserve aspect ratio r."""
        return z * ceil(r * x / z)

    ratio = orig_width / orig_height

    # height is smaller dimension
    if orig_width > orig_height:
        width, height = rnd(ratio, base_size), base_size
        if width > max_size:
            width, height = max_size, rnd(1 / ratio, max_size)
    # width is smaller dimension
    else:
        width, height = base_size, rnd(1 / ratio, base_size)
        if height > max_size:
            width, height = rnd(ratio, max_size), max_size
    
    return width, height
        
def find_fixed_aspect_ratio(
    base_size: int, max_size: int, orig_width: int, orig_height: int
):
    """Copy of `krita_server.utils.sddebz_highres_fix()`.

    This is used by `find_optimal_selection_region()` below to adjust the selected region.
    """
    width, height = calculate_resized_image_dimensions(base_size, max_size, orig_width, orig_height)
    return width / height


def find_optimal_selection_region(
    base_size: int,
    max_size: int,
    orig_x: int,
    orig_y: int,
    orig_width: int,
    orig_height: int,
    canvas_width: int,
    canvas_height: int,
):
    """Adjusts the selected region in order to attempt to preserve the original
    aspect ratio of the selection. This prevents the image from being stretched
    after being scaled and strided.

    After grasping what @sddebz intended to do, I fixed some logical errors &
    made it clearer.

    Iterating the padding is naive, but easier to understand & verify then figuring
    out how to grow the rectangle using the fixed aspect ratio alone while accounting
    for the canvas boundary. Also, it only grows the selection, not shrink, to
    prevent clipping what the user selected.

    Args:
        base_size (int): Native/base input size of the model.
        max_size (int): Max input size to accept.
        orig_x (int): Original left position of selection.
        orig_y (int): Original top position of selection.
        orig_width (int): Original width of selection.
        orig_height (int): Original height of selection.
        canvas_width (int): Canvas width.
        canvas_height (int): Canvas height.

    Returns:
        Tuple[int, int, int, int]: Best x, y, width, height to use.
    """
    orig_ratio = orig_width / orig_height
    fix_ratio = find_fixed_aspect_ratio(base_size, max_size, orig_width, orig_height)

    # h * (w/h - w/h) = w
    xpad_limit = ceil(abs(fix_ratio - orig_ratio) * orig_height) * 2
    # w * (h/w - h/w) = h
    ypad_limit = ceil(abs(1 / fix_ratio - 1 / orig_ratio) * orig_width) * 2

    best_x = orig_x
    best_y = orig_y
    best_width = orig_width
    best_height = orig_height
    best_delta = abs(fix_ratio - orig_ratio)
    for x in range(1, xpad_limit + 1):
        for y in range(1, ypad_limit + 1):
            # account for boundary of canvas
            # padding is on both sides i.e the selection grows while center anchored
            x1 = max(0, orig_x - x // 2)
            x2 = min(canvas_width, x1 + orig_width + x)
            y1 = max(0, orig_y - y // 2)
            y2 = min(canvas_height, y1 + orig_height + y)

            new_width = x2 - x1
            new_height = y2 - y1
            new_ratio = new_width / new_height
            new_delta = abs(fix_ratio - new_ratio)
            if new_delta < best_delta:
                best_delta = new_delta
                best_x = x1
                best_y = y1
                best_width = new_width
                best_height = new_height

    return best_x, best_y, best_width, best_height


def save_img(img: QImage, path: str):
    """Expects QImage"""
    # png is lossless; setting compression to max (0) won't affect quality
    # NOTE: save_img WILL FAIL when using remote backend
    try:
        img.save(path, "PNG", 0)
    except:
        pass


def img_to_ba(img: QImage):
    """Converts QImage to QByteArray"""
    ptr = img.bits()
    ptr.setsize(img.byteCount())
    return QByteArray(ptr.asstring())


def img_to_b64(img: QImage):
    """Converts QImage to base64-encoded string"""
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.WriteOnly)
    img.save(buffer, "PNG", 0)
    return ba.toBase64().data().decode("utf-8")


def b64_to_img(enc: str):
    """Converts base64-encoded string to QImage"""
    ba = QByteArray.fromBase64(enc.encode("utf-8"))
    return QImage.fromData(ba) #Removed explicit format to support other image formats.


def bytewise_xor(msg: bytes, key: bytes):
    """Used for decrypting/encrypting request/response bodies."""
    return bytes(v ^ k for v, k in zip(msg, cycle(key)))


def get_desc_from_resp(resp: dict, type: str = ""):
    """Get description of image generation from backend response."""
    try:
        info = json.loads(resp["info"])
        seeds = info["all_seeds"]
        glayer_desc = f"""[{type}]
Prompt: {info['prompt']},
Negative Prompt: {info['negative_prompt']},
Model: {info['sd_model_hash']},
Sampler: {info['sampler_name']},
Scale: {info['cfg_scale']},
Steps: {info['steps']}"""
        layers_desc = []
        for (seed,) in zip(seeds):
            layers_desc.append(f"Seed: {seed}")
        return glayer_desc, layers_desc
    except:
        return f"[{type}]", cycle([None])


def reset_docker_layout():
    """NOTE: Default stacking of dockers hardcoded here."""
    docker_ids = {
        TAB_SDCOMMON,
        TAB_CONFIG,
        TAB_CONTROLNET,
        TAB_IMG2IMG,
        TAB_TXT2IMG,
        TAB_UPSCALE,
        TAB_INPAINT,
        TAB_PREVIEW,
    }
    instance = Krita.instance()
    # Assumption that currently active window is the main window
    window = instance.activeWindow()
    dockers = {
        d.objectName(): d for d in instance.dockers() if d.objectName() in docker_ids
    }
    qmainwindow = window.qwindow()
    # Reset all dockers
    for d in dockers.values():
        d.setFloating(False)
        d.setVisible(True)
        qmainwindow.addDockWidget(Qt.LeftDockWidgetArea, d)

    qmainwindow.tabifyDockWidget(dockers[TAB_SDCOMMON], dockers[TAB_CONFIG])
    qmainwindow.tabifyDockWidget(dockers[TAB_SDCOMMON], dockers[TAB_CONTROLNET])
    qmainwindow.tabifyDockWidget(dockers[TAB_SDCOMMON], dockers[TAB_PREVIEW])
    qmainwindow.tabifyDockWidget(dockers[TAB_TXT2IMG], dockers[TAB_IMG2IMG])
    qmainwindow.tabifyDockWidget(dockers[TAB_TXT2IMG], dockers[TAB_INPAINT])
    qmainwindow.tabifyDockWidget(dockers[TAB_TXT2IMG], dockers[TAB_UPSCALE])
    dockers[TAB_SDCOMMON].raise_()
    dockers[TAB_INPAINT].raise_()

