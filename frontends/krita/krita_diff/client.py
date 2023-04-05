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
    LONG_TIMEOUT,
    OFFICIAL_ROUTE_PREFIX,
    ROUTE_PREFIX,
    CONTROLNET_ROUTE_PREFIX,
    SHORT_TIMEOUT,
    STATE_DONE,
    STATE_READY,
    STATE_URLERROR,
    THREADED,
)
from .utils import (
    bytewise_xor, 
    fix_prompt, 
    get_ext_args, 
    get_ext_key, 
    img_to_b64, 
    calculate_resized_image_dimensions
)

# NOTE: backend queues up responses, so no explicit need to block multiple requests
# except to prevent user from spamming themselves

# TODO: tab showing all queued up requests (local plugin instance only)


def get_url(cfg: Config, route: str = ..., prefix: str = ROUTE_PREFIX):
    base = cfg("base_url", str)
    if not urlparse(base).scheme in {"http", "https"}:
        return None
    url = urljoin(base, prefix)
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
        headers: dict = ...,
        key: str = None,
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
            key (Union[str, None], Optional): Key to use for encryption/decryption. Defaults to None.
        """
        super(AsyncRequest, self).__init__()
        self.url = url
        self.data = None if data is None else json.dumps(data).encode("utf-8")
        self.headers = {} if headers is ... else headers

        self.key = None
        if isinstance(key, str) and key.strip() != "":
            self.key = key.strip().encode("utf-8")

        if self.key is not None:
            self.headers["X-Encrypted-Body"] = "XOR"
        if timeout is not ...:
            self.timeout = timeout
        if method is ...:
            self.method = "GET" if data is None else "POST"
        else:
            self.method = method
        if self.data is not None:
            if self.key is not None:
                # print(f"Encrypting with ${self.key}:\n{self.data}")
                self.data = bytewise_xor(self.data, self.key)
                # print(f"Encrypt Result:\n{self.data}")
            self.headers["Content-Type"] = "application/json"
            self.headers["Content-Length"] = str(len(self.data))

    def run(self):
        req = Request(self.url, headers=self.headers, method=self.method)
        try:
            with urlopen(req, self.data, self.timeout) as res:
                data = res.read()
                enc_type = res.getheader("X-Encrypted-Body", None)
                assert enc_type in {"XOR", None}, "Unknown server encryption!"
                if enc_type == "XOR":
                    assert self.key, f"Key needed to decrypt server response!"
                    # print(f"Decrypting with ${self.key}:\n{data}")
                    data = bytewise_xor(data, self.key)
                    # print(f"Decrypt Result:\n{data}")
                self.result.emit(json.loads(data))
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
    config_updated = pyqtSignal()

    def __init__(self, cfg: Config, ext_cfg: Config):
        """It is highly dependent on config's structure to the point it writes directly to it. :/"""
        super(Client, self).__init__()
        self.cfg = cfg
        self.ext_cfg = ext_cfg
        self.short_reqs = set()
        self.long_reqs = set()
        # NOTE: this is a hacky workaround for detecting if backend is reachable
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
        except ConnectionError as e:
            self.status.emit(f"{STATE_URLERROR}: connection error during request")
        except Exception as e:
            # self.status.emit(f"{STATE_URLERROR}: Unexpected Error")
            # self.status.emit(str(e))
            assert False, e

    def post(
        self, route, body, cb, base_url=..., is_long=True, ignore_no_connection=False
    ):
        if not ignore_no_connection and not self.is_connected:
            self.status.emit(ERR_NO_CONNECTION)
            return
        url = get_url(self.cfg, route) if base_url is ... else urljoin(base_url, route)
        if not url:
            self.status.emit(ERR_BAD_URL)
            return
        req, start = AsyncRequest.request(
            url,
            body,
            LONG_TIMEOUT if is_long else SHORT_TIMEOUT,
            key=self.cfg("encryption_key"),
        )

        if is_long:
            self.long_reqs.add(req)
        else:
            self.short_reqs.add(req)

        def handler():
            self.long_reqs.discard(req)
            self.short_reqs.discard(req)
            if is_long and len(self.long_reqs) == 0:
                self.status.emit(STATE_DONE)

        req.result.connect(cb)
        req.error.connect(lambda e: self.handle_api_error(e))
        req.finished.connect(handler)
        start()

    def get(self, route, cb, base_url=..., is_long=False, ignore_no_connection=False):
        self.post(
            route,
            None,
            cb,
            base_url=base_url,
            is_long=is_long,
            ignore_no_connection=ignore_no_connection,
        )

    def common_params(self, has_selection):
        """Parameters nearly all the post routes share."""
        tiling = self.cfg("sd_tiling", bool) and not (
            self.cfg("only_full_img_tiling", bool) and has_selection
        )

        # its fine to stuff extra stuff here; pydantic will shave off irrelevant params
        params = dict(
            sd_model=self.cfg("sd_model", str),
            sd_vae=self.cfg("sd_vae", str),
            clip_skip=self.cfg("clip_skip", int),
            batch_count=self.cfg("sd_batch_count", int),
            batch_size=self.cfg("sd_batch_size", int),
            base_size=self.cfg("sd_base_size", int),
            max_size=self.cfg("sd_max_size", int),
            disable_sddebz_highres=self.cfg("disable_sddebz_highres", bool),
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
    
    def options_params(self):
        """Parameters that are specific for the official API options endpoint
        or overriding settings."""
        params = dict(
            sd_model_checkpoint=self.cfg("sd_model", str),
            sd_vae=self.cfg("sd_vae", str),
            CLIP_stop_at_last_layers=self.cfg("clip_skip", int),
            upscaler_for_img2img=self.cfg("upscaler_name", str),
            face_restoration_model=self.cfg("face_restorer_model", str),
            code_former_weight=self.cfg("codeformer_weight", float),
            #Couldn't find filter_nsfw option for official API.
            img2img_fix_steps=self.cfg("do_exact_steps", bool), #Not sure if this is matched correctly.
            img2img_color_correction=self.cfg("img2img_color_correct", bool),
            return_grid=self.cfg("include_grid", bool)
        )
        return params
    
    def official_api_common_params(self, has_selection, width, height,
                                   controlnet_src_imgs):
        """Parameters used by most official API endpoints."""
        tiling = self.cfg("sd_tiling", bool) and not (
            self.cfg("only_full_img_tiling", bool) and has_selection
        )

        params = dict(
            batch_size=self.cfg("sd_batch_size", int),
            width=width,
            height=height,
            tiling=tiling,
            restore_faces=self.cfg("face_restorer_model", str) != "None",
            override_settings=self.options_params(),
            override_settings_restore_afterwards=False,
            alwayson_scripts={}
        )

        if controlnet_src_imgs:
            controlnet_units_param = list()

            for i in range(len(self.cfg("controlnet_unit_list", "QStringList"))):
                if self.cfg(f"controlnet{i}_enable", bool):
                    controlnet_units_param.append(
                        self.controlnet_unit_params(img_to_b64(controlnet_src_imgs[str(i)]), i)
                    )
                
            params["alwayson_scripts"].update({
                "controlnet": {
                    "args": controlnet_units_param
                }
            })
        
        return params
    
    def controlnet_unit_params(self, image: str, unit: int):
        params = dict(
            input_image=image,
            module=self.cfg(f"controlnet{unit}_preprocessor", str),
            model=self.cfg(f"controlnet{unit}_model", str),
            weight=self.cfg(f"controlnet{unit}_weight", float),
            lowvram=self.cfg(f"controlnet{unit}_low_vram", bool),
            processor_res=self.cfg(f"controlnet{unit}_preprocessor_resolution", int),
            threshold_a=self.cfg(f"controlnet{unit}_threshold_a", float),
            threshold_b=self.cfg(f"controlnet{unit}_threshold_b", float),
            guidance_start=self.cfg(f"controlnet{unit}_guidance_start", float),
            guidance_end=self.cfg(f"controlnet{unit}_guidance_end", float),
            guessmode=self.cfg(f"controlnet{unit}_guess_mode", bool)
        )
        return params

    def get_config(self):
        def cb(obj):
            try:
                assert "sample_path" in obj
                assert len(obj["upscalers"]) > 0
                assert len(obj["samplers"]) > 0
                assert len(obj["samplers_img2img"]) > 0
                assert len(obj["face_restorers"]) > 0
                assert len(obj["sd_models"]) > 0
                assert len(obj["sd_vaes"]) > 0
                assert len(obj["scripts_txt2img"]) > 0
                assert len(obj["scripts_img2img"]) > 0
            except:
                self.status.emit(
                    f"{STATE_URLERROR}: incompatible response, are you running the right API?"
                )
                print("Invalid Response:\n", obj)
                return
            
            if "None" not in obj["face_restorers"]:
                obj["face_restorers"].append("None")
            # replace only after verifying
            self.cfg.set("sample_path", obj["sample_path"])
            # NOTE: sorting these lists is risky; ivent 100% verified that I removed all reliance on indexes
            self.cfg.set("upscaler_list", obj["upscalers"])
            self.cfg.set("txt2img_sampler_list", obj["samplers"])
            self.cfg.set("img2img_sampler_list", obj["samplers_img2img"])
            self.cfg.set("inpaint_sampler_list", obj["samplers_img2img"])
            self.cfg.set("txt2img_script_list", list(obj["scripts_txt2img"].keys()))
            self.cfg.set("img2img_script_list", list(obj["scripts_img2img"].keys()))
            self.cfg.set("inpaint_script_list", list(obj["scripts_img2img"].keys()))
            self.cfg.set("face_restorer_model_list", obj["face_restorers"])
            self.cfg.set("sd_model_list", obj["sd_models"])
            self.cfg.set("sd_vae_list", ["Automatic", "None"] + obj["sd_vaes"])

            # extension script cfg
            obj["scripts_inpaint"] = obj["scripts_img2img"]
            for ext_type in {"scripts_txt2img", "scripts_img2img", "scripts_inpaint"}:
                metadata: Dict[str, List[dict]] = obj[ext_type]
                for ext_name, ext_meta in metadata.items():
                    old_val = self.ext_cfg(get_ext_key(ext_type, ext_name))
                    new_val = json.dumps(ext_meta)
                    # Don't overwrite saved script values unless script options changed
                    if new_val != old_val:
                        self.ext_cfg.set(get_ext_key(ext_type, ext_name), new_val)
                        for i, opt in enumerate(ext_meta):
                            key = get_ext_key(ext_type, ext_name, i)
                            self.ext_cfg.set(key, opt["val"])

            self.is_connected = True
            self.status.emit(STATE_READY)
            self.config_updated.emit()

        self.get("config", cb, ignore_no_connection=True)

    def get_controlnet_config(self):
        '''Get models and modules for ControlNet'''
        def check_response(obj, key: str):
            try:
                assert key in obj
            except:
                self.status.emit(
                    f"{STATE_URLERROR}: incompatible response, are you running the right API?"
                )
                print("Invalid Response:\n", obj)
                return
            
        def set_model_list(obj):
            key = "model_list"
            check_response(obj, key)
            self.cfg.set("controlnet_model_list", ["None"] + obj[key])

        def set_preprocessor_list(obj):
            key = "module_list"
            check_response(obj, key)
            self.cfg.set("controlnet_preprocessor_list", obj[key])

        #Get controlnet API url
        url = get_url(self.cfg, prefix=CONTROLNET_ROUTE_PREFIX)
        self.get("model_list", set_model_list, base_url=url)
        self.get("module_list", set_preprocessor_list, base_url=url)

    # def post_options(self):
    #     """Sets the options for the backend, using the official API"""
    #     def cb(response):
    #         assert response is not None, "Backend Error, check terminal"

    #     params = self.options_params()
    #     url = get_url(self.cfg, prefix=OFFICIAL_ROUTE_PREFIX)
    #     self.post("options", params, cb, base_url=url)   

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
            params.update(self.common_params(has_selection))
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

    def post_official_api_txt2img(self, cb, width, height, has_selection, 
                                    controlnet_src_imgs: dict = {}):
        """Uses official API. Leave controlnet_src_imgs empty to not use controlnet."""
        if not self.cfg("just_use_yaml", bool):
            seed = (
                int(self.cfg("txt2img_seed", str))  # Qt casts int as 32-bit int
                if not self.cfg("txt2img_seed", str).strip() == ""
                else -1
            )
            ext_name = self.cfg("txt2img_script", str)
            ext_args = get_ext_args(self.ext_cfg, "scripts_txt2img", ext_name)
            resized_width, resized_height = calculate_resized_image_dimensions(
                self.cfg("sd_base_size", int), self.cfg("sd_max_size", int), width, height
            )
            disable_base_and_max_size = self.cfg("disable_sddebz_highres", bool)
            params = self.official_api_common_params(
                has_selection, 
                resized_width if not disable_base_and_max_size else width, 
                resized_height if not disable_base_and_max_size else height, 
                controlnet_src_imgs
            )
            params.update(
                prompt=fix_prompt(self.cfg("txt2img_prompt", str)),
                negative_prompt=fix_prompt(self.cfg("txt2img_negative_prompt", str)),
                sampler_name=self.cfg("txt2img_sampler", str),
                steps=self.cfg("txt2img_steps", int),
                cfg_scale=self.cfg("txt2img_cfg_scale", float),
                seed=seed,
                enable_hr=self.cfg("txt2img_highres", bool),
                hr_upscaler=self.cfg("upscaler_name", str),
                hr_resize_x=width,
                hr_resize_y=height,
                denoising_strength=self.cfg("txt2img_denoising_strength", float),
                script_name=ext_name if ext_name != "None" else None, #Prevent unrecognized "None" script from backend
                script_args=ext_args if ext_name != "None" else []
            )

            url = get_url(self.cfg, prefix=OFFICIAL_ROUTE_PREFIX)
            self.post("txt2img", params, cb, base_url=url)

    def post_img2img(self, cb, src_img, mask_img, has_selection):
        params = dict(is_inpaint=False, src_img=img_to_b64(src_img))   
        if not self.cfg("just_use_yaml", bool):
            seed = (
                int(self.cfg("img2img_seed", str))  # Qt casts int as 32-bit int
                if not self.cfg("img2img_seed", str).strip() == ""
                else -1
            )
            ext_name = self.cfg("img2img_script", str)
            ext_args = get_ext_args(self.ext_cfg, "scripts_img2img", ext_name)
            params.update(self.common_params(has_selection))
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

    def post_official_api_img2img(self, cb, src_img, width, height, has_selection, 
                                controlnet_src_imgs: dict = {}):
        """Uses official API. Leave controlnet_src_imgs empty to not use controlnet."""
        params = dict(init_images=[img_to_b64(src_img)])
        if not self.cfg("just_use_yaml", bool):
            seed = (
                int(self.cfg("img2img_seed", str))  # Qt casts int as 32-bit int
                if not self.cfg("img2img_seed", str).strip() == ""
                else -1
            )
            ext_name = self.cfg("img2img_script", str)
            ext_args = get_ext_args(self.ext_cfg, "scripts_img2img", ext_name)
            resized_width, resized_height = calculate_resized_image_dimensions(
                self.cfg("sd_base_size", int), self.cfg("sd_max_size", int), width, height
            )
            disable_base_and_max_size = self.cfg("disable_sddebz_highres", bool)
            params.update(self.official_api_common_params(
                has_selection, 
                resized_width if not disable_base_and_max_size else width, 
                resized_height if not disable_base_and_max_size else height, 
                controlnet_src_imgs
            ))
            params.update(
                prompt=fix_prompt(self.cfg("img2img_prompt", str)),
                negative_prompt=fix_prompt(self.cfg("img2img_negative_prompt", str)),
                sampler_name=self.cfg("img2img_sampler", str),
                steps=self.cfg("img2img_steps", int),
                cfg_scale=self.cfg("img2img_cfg_scale", float),
                seed=seed,
                denoising_strength=self.cfg("img2img_denoising_strength", float),
                script_name=ext_name if ext_name != "None" else None,
                script_args=ext_args if ext_name != "None" else []
            )

        url = get_url(self.cfg, prefix=OFFICIAL_ROUTE_PREFIX)
        self.post("img2img", params, cb, base_url=url)

    def post_inpaint(self, cb, src_img, mask_img, has_selection):
        assert mask_img, "Inpaint layer is needed for inpainting!"
        params = dict(
            is_inpaint=True, src_img=img_to_b64(src_img), mask_img=img_to_b64(mask_img)
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
            params.update(self.common_params(has_selection))
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
                # mask_blur=self.cfg("inpaint_mask_blur", int),
                inpainting_fill=fill,
                # inpaint_full_res=self.cfg("inpaint_full_res", bool),
                # inpaint_full_res_padding=self.cfg("inpaint_full_res_padding", int),
                inpaint_mask_weight=self.cfg("inpaint_mask_weight", float),
                include_grid=False,  # it is never useful for inpaint mode
            )

        self.post("img2img", params, cb)

    def post_official_api_inpaint(self, cb, src_img, mask_img, width, height, has_selection, 
                                controlnet_src_imgs: dict = {}):
        """Uses official API. Leave controlnet_src_imgs empty to not use controlnet."""
        assert mask_img, "Inpaint layer is needed for inpainting!"
        params = dict(
            init_images=[img_to_b64(src_img)], mask=img_to_b64(mask_img)
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
            resized_width, resized_height = calculate_resized_image_dimensions(
                self.cfg("sd_base_size", int), self.cfg("sd_max_size", int), width, height
            )
            invert_mask = self.cfg("inpaint_invert_mask", bool)
            disable_base_and_max_size = self.cfg("disable_sddebz_highres", bool)
            params.update(self.official_api_common_params(
                has_selection, 
                resized_width if not disable_base_and_max_size else width, 
                resized_height if not disable_base_and_max_size else height, 
                controlnet_src_imgs
            ))
            params.update(
                prompt=fix_prompt(self.cfg("inpaint_prompt", str)),
                negative_prompt=fix_prompt(self.cfg("inpaint_negative_prompt", str)),
                sampler_name=self.cfg("inpaint_sampler", str),
                steps=self.cfg("inpaint_steps", int),
                cfg_scale=self.cfg("inpaint_cfg_scale", float),
                seed=seed,
                denoising_strength=self.cfg("inpaint_denoising_strength", float),
                script_name=ext_name if ext_name != "None" else None,
                script_args=ext_args if ext_name != "None" else [],
                inpainting_mask_invert=0 if not invert_mask else 1,
                inpainting_fill=fill,
                mask_blur=0,
                inpaint_full_res=False
                #not sure what's the equivalent of mask weight for official API
            )

            params["override_settings"]["return_grid"] = False

        url = get_url(self.cfg, prefix=OFFICIAL_ROUTE_PREFIX)
        self.post("img2img", params, cb, base_url=url)

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

    def post_controlnet_preview(self, cb, src_img):
        unit = self.cfg("controlnet_unit")
        params = (
            {
                "controlnet_module": self.cfg(f"controlnet{unit}_preprocessor"),
                "controlnet_input_images": [img_to_b64(src_img)],
                "controlnet_processor_res": self.cfg(f"controlnet{unit}_preprocessor_resolution"),
                "controlnet_threshold_a": self.cfg(f"controlnet{unit}_threshold_a"),
                "controlnet_threshold_b": self.cfg(f"controlnet{unit}_threshold_b")
            } #Not sure if it's necessary to make the just_use_yaml validation here
        )
        url = get_url(self.cfg, prefix=CONTROLNET_ROUTE_PREFIX)
        self.post("detect", params, cb, url)

    def post_interrupt(self, cb):
        # get official API url
        url = get_url(self.cfg, prefix=OFFICIAL_ROUTE_PREFIX)
        self.post("interrupt", {}, cb, base_url=url)

    def get_progress(self, cb):
        # get official API url
        url = get_url(self.cfg, prefix=OFFICIAL_ROUTE_PREFIX)
        self.get("progress", cb, base_url=url)
