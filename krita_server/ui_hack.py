"""
Attempting to map Gradio UI elements present in scripts to allow
converting to pyQt elements on the plugin side.
"""

import gradio as gr
from webui import modules


def inspect_ui(script: modules.scripts.Script, is_img2img: bool):
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
