"""
Attempting to map Gradio UI elements present in scripts to allow
converting to pyQt elements on the plugin side.
"""

import logging
from typing import List, Tuple

import gradio as gr
import modules

from .config import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


def inspect_ui(script: modules.scripts.Script, is_img2img: bool):
    """Get metadata about accepted arguments by inspecting GUI."""
    with gr.Blocks():
        elems = script.ui(is_img2img)

    metadata = []
    for elem in elems:
        data = {
            "type": "None",
            "label": elem.label,
            "val": elem.value,
            "is_index": False,
        }
        if isinstance(elem, gr.HTML):
            data.update(val="")
        elif isinstance(elem, gr.Markdown):
            data.update(val="")
        elif isinstance(elem, gr.Slider):
            data.update(
                type="range",
                min=elem.minimum,
                max=elem.maximum,
                step=elem.step,
            )
        elif isinstance(elem, gr.Radio):
            data.update(
                type="combo",
                is_index=elem.type == "index",
                opts=elem.choices,
            )
        elif isinstance(elem, gr.Dropdown):
            data.update(
                type="combo",
                is_index=elem.type == "index",
                opts=elem.choices,
            )
        elif isinstance(elem, gr.Textbox):
            data.update(
                type="text",
            )
        elif isinstance(elem, gr.Checkbox):
            data.update(
                type="checkbox",
            )
        elif isinstance(elem, gr.CheckboxGroup):
            data.update(
                type="multiselect",
                is_index=elem.type == "index",
                opts=elem.choices,
            )
        elif isinstance(elem, gr.File):
            data.update(val="")  # unsupported
        else:
            data.update(val="")  # unsupported
        metadata.append(data)

    return metadata


img2img_script_meta = None
txt2img_script_meta = None


def get_scripts_metadata(is_img2img: bool):
    """Get metadata about accepted arguments for scripts."""
    # NOTE: inspect_ui is quite slow, so cache this
    global txt2img_script_meta, img2img_script_meta
    if is_img2img:
        runner = modules.scripts.scripts_img2img
    else:
        runner = modules.scripts.scripts_txt2img
    metadata = {"None": []}
    if (
        is_img2img
        and img2img_script_meta
        and len(img2img_script_meta) - 1 == len(runner.titles)
    ):
        return img2img_script_meta
    elif txt2img_script_meta and len(txt2img_script_meta) - 1 == len(runner.titles):
        return txt2img_script_meta

    for name, script in zip(runner.titles, runner.selectable_scripts):
        metadata[name] = inspect_ui(script, is_img2img)
    if is_img2img:
        img2img_script_meta = metadata
    else:
        txt2img_script_meta = metadata
    return metadata


def get_script_info(
    script_name: str, is_img2img: bool
) -> Tuple[int, modules.scripts.Script, List[dict]]:
    """Get index of script, script instance and argument metadata by name.

    Args:
        script_name (str): Exact name of script.
        is_img2img (bool): Whether the script is for img2img or txt2img.

    Raises:
        KeyError: Script cannot be found.

    Returns:
        Tuple[int, Script, List[dict]]: Index of script, script itself and arguments metadata.
    """
    if is_img2img:
        runner = modules.scripts.scripts_img2img
    else:
        runner = modules.scripts.scripts_txt2img
    # in API, index 0 means no script, scripts are indexed from 1 onwards
    names = ["None"] + runner.titles
    if script_name == "None":
        return 0, None, []
    for i, n in enumerate(names):
        if n == script_name:
            script = runner.selectable_scripts[i - 1]
            return i, script, get_scripts_metadata(is_img2img)[n]
    raise KeyError(f"script not found for type {type}: {script_name}")


def process_script_args(
    script_ind: int, script: modules.scripts.Script, meta: List[dict], args: list
) -> list:
    """Get the position arguments required."""
    if script is None:
        return [0]  # 0th element selects which script to use. 0 is None.

    # convert strings back to indexes
    for i, (o, arg) in enumerate(zip(meta, args)):
        if o["is_index"]:
            if isinstance(arg, list):
                args[i] = [o["opts"].index(v) for v in arg]
            else:
                args[i] = o["opts"].index(arg)

    log.info(
        f"Script selected: {script.filename}, Args Range: [{script.args_from}:{script.args_to}]"
    )
    # pad the args like the internal API requires...
    args = [script_ind] + [0] * (script.args_from - 1) + args
    log.info(f"Script args:\n{args}")
    return args
