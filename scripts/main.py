import logging

import backend
import gradio as gr
from backend.config import LOGGER_NAME, ROUTE_PREFIX, SCRIPT_ID, SCRIPT_NAME
from fastapi import FastAPI
from modules import script_callbacks, scripts, shared


class BackendScript(scripts.Script):
    def title(self):
        return SCRIPT_NAME

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        text = gr.Text(label="No UI for now!")
        return [text]

    def process(self, _):
        pass


def on_app_started(demo: gr.Blocks, app: FastAPI):
    if shared.cmd_opts.api:
        app.include_router(backend.router, prefix=ROUTE_PREFIX, tags=[SCRIPT_NAME])
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(name)s:%(levelname)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    # if you wanted to do anything massive to the UI, you could modify demo, but why?


def on_ui_settings():
    # hook to add our own settings to the settings tab
    pass


def on_ui_tabs():
    # hook to create our own UI tab
    with gr.Blocks(analytics_enabled=False) as interface:
        text = gr.Text(label="No UI for now!")

    return [(interface, SCRIPT_NAME, SCRIPT_ID)]


# NOTE: see modules/script_callbacks.py for all callbacks
script_callbacks.on_app_started(on_app_started)
script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
