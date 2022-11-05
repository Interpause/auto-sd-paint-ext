import json
import socket
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from krita import QObject, QThread, pyqtSignal

from .config import Config
from .defaults import (
    ERR_BAD_URL,
    ERR_NO_CONNECTION,
    GET_CONFIG_TIMEOUT,
    POST_TIMEOUT,
    ROUTE_PREFIX,
    STATE_READY,
    STATE_URLERROR,
    THREADED,
)
from .utils import fix_prompt, get_ext_args, get_ext_key, img_to_b64

# NOTE: backend queues up responses, so no explicit need to block multiple requests
# except to prevent user from spamming themselves


def get_url(cfg: Config, route: str = ...):
    base = cfg("base_url", str)
    if not urlparse(base).scheme in ("http", "https"):
        return None
    url = urljoin(base, ROUTE_PREFIX)
    if route is not ...:
        url = urljoin(url, route)
    # print("url:", url)
    return url


# krita doesn't reexport QtNetwork
class AsyncRequest(QObject):
    timeout = None
    finished = pyqtSignal()
    result = pyqtSignal(object)
    error = pyqtSignal(Exception)

    def __init__(
        self,
        url: str,
        data: Any = None,
        timeout: int = ...,
        method: str = ...,
        headers: dict = {},
    ):
        """Create an AsyncRequest object.

        By default, AsyncRequest has no timeout, will infer whether it is "POST"
        or "GET" based on the presence of `data` and uses JSON to transmit. It
        also assumes the response is JSON.

        Args:
            url (str): URL to request from.
            data (Any, optional): Payload to send. Defaults to None.
            timeout (int, optional): Timeout for request. Defaults to `...`.
            method (str, optional): Which HTTP method to use. Defaults to `...`.
        """
        super(AsyncRequest, self).__init__()
        self.url = url
        self.data = None if data is None else json.dumps(data).encode("utf-8")
        if timeout is not ...:
            self.timeout = timeout
        if method is ...:
            self.method = "GET" if data is None else "POST"
        else:
            self.method = method
        self.headers = headers
        if self.data is not None:
            self.headers["Content-Type"] = "application/json"
            self.headers["Content-Length"] = str(len(self.data))

    def run(self):
        req = Request(self.url, headers=self.headers, method=self.method)
        try:
            with urlopen(req, self.data, self.timeout) as res:
                self.result.emit(json.loads(res.read()))
        except Exception as e:
            self.error.emit(e)
        finally:
            self.finished.emit()

    @classmethod
    def request(cls, *args, **kwargs):
        req = cls(*args, **kwargs)
        if THREADED:
            thread = QThread()
            # NOTE: need to keep reference to thread or it gets destroyed
            req.thread = thread
            req.moveToThread(thread)
            thread.started.connect(req.run)
            req.finished.connect(thread.quit)
            # NOTE: is this a memory leak?
            # For some reason, deleteLater occurs while thread is still running, resulting in crash
            # req.finished.connect(req.deleteLater)
            # thread.finished.connect(thread.deleteLater)
            return req, lambda: thread.start()
        else:
            return req, lambda: req.run()


class Client(QObject):
    status = pyqtSignal(str)
    """error message, Exception object"""

    def __init__(self, cfg: Config, ext_cfg: Config):
        """It is highly dependent on config's structure to the point it writes directly to it. :/"""
        super(Client, self).__init__()
        self.cfg = cfg
        self.ext_cfg = ext_cfg
        self.reqs = []
        # NOTE: this is a hacky workaround for detecting if backend is reachable
        # this is to prevent zombie post requests (since they have no timeout)
        self.is_connected = False

    def handle_api_error(self, exc: Exception):
        """Handle exceptions that can occur while interacting with the backend."""
        self.is_connected = False
        try:
            # wtf python? socket raises an error that isnt an Exception??
            if isinstance(exc, socket.timeout):
                raise TimeoutError
            else:
                raise exc
        except URLError as e:
            self.status.emit(f"{STATE_URLERROR}: {e.reason}")
        except TimeoutError as e:
            self.status.emit(f"{STATE_URLERROR}: response timed out")
        except json.JSONDecodeError as e:
            self.status.emit(f"{STATE_URLERROR}: invalid JSON response")
        except ValueError as e:
            self.status.emit(f"{STATE_URLERROR}: Invalid backend URL")
        except Exception as e:
            # self.status.emit(f"{STATE_URLERROR}: Unexpected Error")
            # self.status.emit(str(e))
            assert False, e

    def post(self, route, body, cb, base_url=...):
        if not self.is_connected:
            self.status.emit(ERR_NO_CONNECTION)
            return
        url = get_url(self.cfg, route) if base_url is ... else urljoin(base_url, route)
        if not url:
            self.status.emit(ERR_BAD_URL)
            return
        # TODO: how to cancel this? destroy the thread after sending API interrupt request?
        req, start = AsyncRequest.request(url, body, POST_TIMEOUT)
        self.reqs.append(req)
        req.finished.connect(lambda: self.reqs.remove(req))
        req.result.connect(cb)
        req.error.connect(self.handle_api_error)
        start()

    def get_common_params(self, has_selection):
        """Parameters nearly all the post routes share."""
        tiling = self.cfg("sd_tiling", bool) and not (
            self.cfg("only_full_img_tiling", bool) and has_selection
        )

        # its fine to stuff extra stuff here; pydantic will shave off irrelevant params
        params = dict(
            sd_model=self.cfg("sd_model", str),
            batch_count=self.cfg("sd_batch_count", int),
            batch_size=self.cfg("sd_batch_size", int),
            base_size=self.cfg("sd_base_size", int),
            max_size=self.cfg("sd_max_size", int),
            tiling=tiling,
            upscaler_name=self.cfg("upscaler_name", str),
            restore_faces=self.cfg("face_restorer_model", str) != "None",
            face_restorer=self.cfg("face_restorer_model", str),
            codeformer_weight=self.cfg("codeformer_weight", float),
            filter_nsfw=self.cfg("filter_nsfw", bool),
            do_exact_steps=self.cfg("do_exact_steps", bool),
            include_grid=self.cfg("include_grid", bool),
            save_samples=self.cfg("save_temp_images", bool),
        )
        return params

    def get_config(self) -> bool:
        def cb(obj):
            try:
                assert "sample_path" in obj
                assert len(obj["upscalers"]) > 0
                assert len(obj["samplers"]) > 0
                assert len(obj["samplers_img2img"]) > 0
                assert len(obj["face_restorers"]) > 0
                assert len(obj["sd_models"]) > 0
                assert len(obj["scripts_txt2img"]) > 0
                assert len(obj["scripts_img2img"]) > 0
            except:
                self.status.emit(
                    f"{STATE_URLERROR}: incompatible response, are you running the right API?"
                )
                return

            # replace only after verifying
            self.cfg.set("sample_path", obj["sample_path"])
            self.cfg.set("upscaler_list", obj["upscalers"])
            self.cfg.set("txt2img_sampler_list", obj["samplers"])
            self.cfg.set("img2img_sampler_list", obj["samplers_img2img"])
            self.cfg.set("inpaint_sampler_list", obj["samplers_img2img"])
            self.cfg.set("txt2img_script_list", list(obj["scripts_txt2img"].keys()))
            self.cfg.set("img2img_script_list", list(obj["scripts_img2img"].keys()))
            self.cfg.set("inpaint_script_list", list(obj["scripts_img2img"].keys()))
            self.cfg.set("face_restorer_model_list", obj["face_restorers"])
            self.cfg.set("sd_model_list", obj["sd_models"])

            # extension script cfg
            obj["scripts_inpaint"] = obj["scripts_img2img"]
            for ext_type in ("scripts_txt2img", "scripts_img2img", "scripts_inpaint"):
                metadata: Dict[str, List[dict]] = obj[ext_type]
                self.ext_cfg.set(f"{ext_type}_len", len(metadata))
                for ext_name, ext_meta in metadata.items():
                    old_val = self.ext_cfg(get_ext_key(ext_type, ext_name))
                    new_val = json.dumps(ext_meta)
                    if new_val != old_val:
                        self.ext_cfg.set(get_ext_key(ext_type, ext_name), new_val)
                        for i, opt in enumerate(ext_meta):
                            key = get_ext_key(ext_type, ext_name, i)
                            self.ext_cfg.set(key, opt["val"])

            self.is_connected = True
            self.status.emit(STATE_READY)

        # only get config if there are no pending post requests jamming the backend
        # NOTE: this might prevent get_config() from ever working if zombie requests can happen
        if len(self.reqs) > 0:
            return

        url = get_url(self.cfg, "config")
        if not url:
            self.status.emit(ERR_BAD_URL)
            return
        req, start = AsyncRequest.request(url, None, GET_CONFIG_TIMEOUT)
        self.reqs.append(req)
        req.finished.connect(lambda: self.reqs.remove(req))
        req.result.connect(cb)
        req.error.connect(self.handle_api_error)
        start()

    def post_txt2img(self, cb, width, height, has_selection):
        params = dict(orig_width=width, orig_height=height)
        if not self.cfg("just_use_yaml", bool):
            seed = (
                int(self.cfg("txt2img_seed", str))  # Qt casts int as 32-bit int
                if not self.cfg("txt2img_seed", str).strip() == ""
                else -1
            )
            ext_name = self.cfg("txt2img_script", str)
            ext_args = get_ext_args(self.ext_cfg, "scripts_txt2img", ext_name)
            params.update(self.get_common_params(has_selection))
            params.update(
                prompt=fix_prompt(self.cfg("txt2img_prompt", str)),
                negative_prompt=fix_prompt(self.cfg("txt2img_negative_prompt", str)),
                sampler_name=self.cfg("txt2img_sampler", str),
                steps=self.cfg("txt2img_steps", int),
                cfg_scale=self.cfg("txt2img_cfg_scale", float),
                seed=seed,
                highres_fix=self.cfg("txt2img_highres", bool),
                denoising_strength=self.cfg("txt2img_denoising_strength", float),
                script=ext_name,
                script_args=ext_args,
            )

        self.post("txt2img", params, cb)

    def post_img2img(self, cb, src_img, mask_img, has_selection):
        params = dict(
            mode=0, src_img=img_to_b64(src_img), mask_img=img_to_b64(mask_img)
        )
        if not self.cfg("just_use_yaml", bool):
            seed = (
                int(self.cfg("img2img_seed", str))  # Qt casts int as 32-bit int
                if not self.cfg("img2img_seed", str).strip() == ""
                else -1
            )
            ext_name = self.cfg("img2img_script", str)
            ext_args = get_ext_args(self.ext_cfg, "scripts_img2img", ext_name)
            params.update(self.get_common_params(has_selection))
            params.update(
                prompt=fix_prompt(self.cfg("img2img_prompt", str)),
                negative_prompt=fix_prompt(self.cfg("img2img_negative_prompt", str)),
                sampler_name=self.cfg("img2img_sampler", str),
                steps=self.cfg("img2img_steps", int),
                cfg_scale=self.cfg("img2img_cfg_scale", float),
                denoising_strength=self.cfg("img2img_denoising_strength", float),
                color_correct=self.cfg("img2img_color_correct", bool),
                script=ext_name,
                script_args=ext_args,
                seed=seed,
            )

        self.post("img2img", params, cb)

    def post_inpaint(self, cb, src_img, mask_img, has_selection):
        params = dict(
            mode=1, src_img=img_to_b64(src_img), mask_img=img_to_b64(mask_img)
        )
        if not self.cfg("just_use_yaml", bool):
            seed = (
                int(self.cfg("inpaint_seed", str))  # Qt casts int as 32-bit int
                if not self.cfg("inpaint_seed", str).strip() == ""
                else -1
            )
            fill = self.cfg("inpaint_fill_list", "QStringList").index(
                self.cfg("inpaint_fill", str)
            )
            ext_name = self.cfg("inpaint_script", str)
            ext_args = get_ext_args(self.ext_cfg, "scripts_inpaint", ext_name)
            params.update(self.get_common_params(has_selection))
            params.update(
                prompt=fix_prompt(self.cfg("inpaint_prompt", str)),
                negative_prompt=fix_prompt(self.cfg("inpaint_negative_prompt", str)),
                sampler_name=self.cfg("inpaint_sampler", str),
                steps=self.cfg("inpaint_steps", int),
                cfg_scale=self.cfg("inpaint_cfg_scale", float),
                denoising_strength=self.cfg("inpaint_denoising_strength", float),
                color_correct=self.cfg("inpaint_color_correct", bool),
                script=ext_name,
                script_args=ext_args,
                seed=seed,
                invert_mask=self.cfg("inpaint_invert_mask", bool),
                mask_blur=self.cfg("inpaint_mask_blur", int),
                inpainting_fill=fill,
                inpaint_full_res=self.cfg("inpaint_full_res", bool),
                inpaint_full_res_padding=self.cfg("inpaint_full_res_padding", int),
                include_grid=False,  # it is never useful for inpaint mode
            )

        self.post("img2img", params, cb)

    def post_upscale(self, cb, src_img):
        params = (
            {
                "src_img": img_to_b64(src_img),
                "upscaler_name": self.cfg("upscale_upscaler_name", str),
                "downscale_first": self.cfg("upscale_downscale_first", bool),
            }
            if not self.cfg("just_use_yaml", bool)
            else {"src_img": img_to_b64(src_img)}
        )
        self.post("upscale", params, cb)
