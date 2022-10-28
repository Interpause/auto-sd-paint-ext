import gradio as gr
import main
from modules import script_callbacks, scripts

has_started = False
"""Theres no on_init hook, so we ensure our hijack runs only once ourselves"""
server = None


class BackendScript(scripts.Script):
    def title(self):
        return "Interpause Backend"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        text = gr.Text("No UI for now!")
        return [text]

    def process(self, _):
        pass


def on_model_loaded(sd_model):
    # hook to modify model when it is loaded
    pass


def on_ui_settings():
    # hook to add our own settings to the settings tab
    global has_started, server
    if has_started:
        return
    has_started = True
    server = main.start()


def on_ui_tabs():
    # hook to create our own UI tab
    with gr.Blocks(analytics_enabled=False) as interface:
        text = gr.Text("No UI for now!")

    return [(interface, "Interpause Backend", "interpause_backend_api")]


script_callbacks.on_model_loaded(on_model_loaded)
script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
# on_before_image_saved
# on_image_saved
