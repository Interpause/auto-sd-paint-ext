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
        if isinstance(elem, gr.HTML):
            metadata.append({})
        elif isinstance(elem, gr.Markdown):
            metadata.append({})
        elif isinstance(elem, gr.Slider):
            metadata.append(
                dict(
                    type="range",
                    label=elem.label,
                    min=elem.minimum,
                    max=elem.maximum,
                    step=elem.step,
                    val=elem.value,
                )
            )
        elif isinstance(elem, gr.Radio):
            metadata.append(
                dict(
                    type="combo",
                    label=elem.label,
                    opts=elem.choices,
                    val=elem.value,
                )
            )
        elif isinstance(elem, gr.Dropdown):
            metadata.append(
                dict(
                    type="combo",
                    label=elem.label,
                    opts=elem.choices,
                    val=elem.value,
                )
            )
        elif isinstance(elem, gr.Textbox):
            metadata.append(
                dict(
                    type="text",
                    label=elem.label,
                    val="",
                )
            )
        elif isinstance(elem, gr.Checkbox):
            metadata.append(
                dict(
                    type="checkbox",
                    label=elem.label,
                    val=elem.value,
                )
            )
        elif isinstance(elem, gr.CheckboxGroup):
            metadata.append(
                dict(
                    type="multiselect",
                    label=elem.label,
                    val=elem.value,
                )
            )
        elif isinstance(elem, gr.File):
            # unsupported
            metadata.append({})
        else:
            # unsupported
            metadata.append({})

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
