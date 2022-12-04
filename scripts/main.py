import logging
from pathlib import Path

import backend
import gradio as gr
from backend.app import app_encryption_middleware
from backend.config import LOGGER_NAME, ROUTE_PREFIX, SCRIPT_ID, SCRIPT_NAME
from backend.utils import get_encrypt_key
from fastapi import FastAPI
from modules import script_callbacks, scripts, shared

PLUGIN_LOCATION = Path(scripts.basedir()) / "frontends" / "krita"


class BackendScript(scripts.Script):
    def title(self):
        return SCRIPT_NAME

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return []

    def process(self, _):
        pass


started = False


def on_app_started(demo: gr.Blocks, app: FastAPI):
    # NOTE: There is currently a glitch where the on_app_started() callback is called twice
    # Surprisingly, it only breaks the encryption middleware and causes duplicate logs
    # Below is a workaround to fix said issues
    # Downside is that for now, restarting Gradio via the webUI will just break the extension
    global started
    if started:
        return
    started = True

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

    if shared.cmd_opts.api:
        app.include_router(backend.router, prefix=ROUTE_PREFIX, tags=[SCRIPT_NAME])
        app.middleware("http")(app_encryption_middleware)
        # on first run, this creates a key file
        get_encrypt_key()
        if not shared.cmd_opts.listen:
            logger.info(
                "Add --listen to COMMANDLINE_ARGS to enable usage as a remote backend."
            )
    else:
        logger.warning("COMMANDLINE_ARGS does not contain --api, API won't be mounted.")
    # if you wanted to do anything massive to the UI, you could modify demo, but why?


def on_ui_settings():
    # hook to add our own settings to the settings tab
    pass


def krita_help(folder):
    folder = "<path_to_pykrita>" if not folder else folder
    return f"""
        Search for "Command Prompt" in the Start Menu, right-click and click "Run as Administrator...", paste the follow commands and hit Enter:
        ```bat
        mklink /j "{folder}\\krita_diff" "{(PLUGIN_LOCATION / 'krita_diff').resolve()}"
        mklink "{folder}\\krita_diff.desktop" "{(PLUGIN_LOCATION / 'krita_diff.desktop').resolve()}"
        ```

        Linux command:
        ```sh
        ln -s "{(PLUGIN_LOCATION / 'krita_diff').resolve()}" "{folder}/krita_diff"
        ln -s "{(PLUGIN_LOCATION / 'krita_diff.desktop').resolve()}" "{folder}/krita_diff.desktop"
        ```
        """


def on_ui_tabs():
    # hook to create our own UI tab
    with gr.Blocks(analytics_enabled=False) as interface:
        gr.Markdown(
            """
        ### Generate Krita Plugin Symlink Command

        1. Launch Krita.
        2. On the menubar, go to `Settings > Manage Resources...`.
        3. In the window that appears, click `Open Resource Folder`.
        4. In the file explorer that appears, look for a folder called `pykrita` or create it.
        5. Enter the `pykrita` folder and copy the folder location from the address bar.
        6. Paste the folder location below.
        """
        )
        folder = gr.Textbox(
            placeholder="C:\\\\...\\pykrita", label="Pykrita Folder Location", lines=1
        )
        out = gr.Markdown(krita_help(""))
        folder.change(krita_help, folder, out)
        gr.Markdown(
            """
        **NOTE**: Symlinks will break if you move or rename the repository or any 
        of its parent folders or otherwise change the path such that the symlink 
        becomes invalid. In which case, repeat the above steps with the new `pykrita` 
        folder location and (auto-detected) repository location.

        **NOTE**: Ensure `webui-user.bat`/`webui-user.sh` contains `--api` in `COMMANDLINE_ARGS`!
        """
        )
        gr.Markdown(
            """
            ### Enabling the Krita Plugin

            1. Restart Krita.
            2. On the menubar, go to `Settings > Configure Krita...`
            3. On the left sidebar, go to `Python Plugin Manager`.
            4. Look for `Stable Diffusion Plugin` and tick the checkbox.
            5. Restart Krita again for changes to take effect.

            The `SD Plugin` docked window should appear on the left of the Krita window. If it does not, look on the menubar under `Settings > Dockers` for `SD Plugin`.

            ### Next Steps

            - [Troubleshooting](https://github.com/Interpause/auto-sd-paint-ext/wiki/Troubleshooting)
            - [Update Guide](https://github.com/Interpause/auto-sd-paint-ext/wiki/Update-Guide)
            - [Usage Guide](https://github.com/Interpause/auto-sd-paint-ext/wiki/Usage-Guide)
            """
        )
        gr.Markdown("TODO: Control/status panel")

    return [(interface, "auto-sd-paint-ext Guide/Panel", SCRIPT_ID)]


# NOTE: see modules/script_callbacks.py for all callbacks
script_callbacks.on_app_started(on_app_started)
script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
