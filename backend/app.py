from __future__ import annotations
from contextlib import closing

import logging
import os
import time

import modules
import gradio as gr  # Used for A1111 api calls
import inspect  # Used to determine what parameters are needed/missing
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from modules import shared
from modules.call_queue import wrap_gradio_gpu_call
from modules import processing
from modules.shared import opts, cmd_opts
from modules.generation_parameters_copypaste import create_override_settings_dict
from PIL import Image, ImageOps
from starlette.concurrency import iterate_in_threadpool

from .config import LOGGER_NAME, NAME_SCRIPT_LOOPBACK, NAME_SCRIPT_UPSCALE
from .script_hack import get_script_info, get_scripts_metadata, process_script_args
from .structs import (
    ConfigResponse,
    ImageResponse,
    Img2ImgRequest,
    Txt2ImgRequest,
    UpscaleRequest,
    UpscaleResponse,
)
from .utils import (
    b64_to_img,
    bytewise_xor,
    get_encrypt_key,
    get_sampler_index,
    get_upscaler_index,
    img_to_b64,
    load_config,
    merge_default_config,
    parse_prompt,
    prepare_backend,
    prepare_mask,
    save_img,
    sddebz_highres_fix,
)

router = APIRouter()

log = logging.getLogger(LOGGER_NAME)

# NOTE: how to run a script
# - get scripts_txt2img/scripts_img2img from modules.scripts
# - construct array args, where 0th element is selected script
# - refer to script.args_from & script.args_to to figure out which elements in
#   array args to populate
#
# The way scripts are handled is they are loaded one by one, append to a list of
# scripts, which each script taking up "slots" in the input args array.
# So the more scripts, the longer array args would be for the last script.

# NOTE: where to draw the line on what is done by the backend vs the frontend?
# TODO: Create separate Outpainting route, add img2img structs to Upscale route
# - yes I know its highly inconsistent what should be a route or not, but to prevent
#   incredibly hacky workarounds on the frontend for script calling, it should be
#   done by the backend, which has better access to the script information.
# - Upscale tab UI:
#    - Upscaler dropdown + 0.5x downscale checkbox + SD upscale checkbox
#    - SD upscale checkbox hides 0.5x downscale checkbox, renames upscaler dropdown
#    - to prescaler, and shows modified img2img UI (ofc uses its own cfg namespace)
# - Outpaint tab UI:
#    - modified img2img UI with own cfg namespace
#    - try and hijack more control (Pixel to expand per direction instead of all directions)
#    - self-sketch mode: basically sketch + inpaint but the inpaint mask is auto-calculated
#    - option to select poor man, mk 2 or self-sketch
# TODO: Consider using pipeline directly instead of Gradio API for less surprises & better control


def get_required_params(function_path, req, height, width, image=None, mask=None):
    """Return the params for ANY version of A1111 or SD.Next
        If a parameter is not found, it'll try to autocomplete the missing parameter
        Returns the parameters required for this UI (A1111, SD.Next, or other clones)

    Args:
        function_path: the function used by the Gradio API (such as modules.txt2img.txt2img or modules.img2img.img2img)
        req: either Txt2ImgRequest or Img2ImgRequest
        height: int
        width: int
        image: Image
        mask: Image
    Returns:
        List: params,
        Dict: warnings
    """

    # NOTE:
    # - image & mask repeated due to Gradio API have separate tabs for each mode...
    # - mask is used only in inpaint mode
    # - mask_mode determines whether init_img_with_mask or init_img_inpaint is used,
    #   I don't know why
    # - new color sketch functionality in webUI is irrelevant so None is used for their options.
    # - the internal code for img2img is confusing and duplicative...

    # NOTE: DO NOT REMOVE PARAMS! Only add to this list.
    # Even if they've been deprecated by the version of WebUI you use, old params are still helpful for others running other UIs on other versions.

    params = {
        'batch_size': req.batch_size,
        'cfg_scale': req.cfg_scale,
        'clip_skip': req.clip_skip,
        'denoising_strength': req.denoising_strength, # Used for img2img, and txt2img only when high res fix in use
        'diffusers_guidance_rescale': 0.7,  # 0.7 is the default value in SD.Next's UI
        'enable_hr': req.highres_fix,  # High res fix
        'enable_refiner': False,
        'full_quality': True,
        'height': height,
        'hr_negative_prompt': parse_prompt(req.negative_prompt),
        'hr_prompt': parse_prompt(req.prompt),
        'hr_resize_x': req.orig_width if hasattr(req, 'orig_width') else width,
        'hr_resize_y': req.orig_height if hasattr(req, 'orig_height') else height,
        'hr_checkpoint_name': req.sd_model,
        'hr_sampler_index': get_sampler_index(req.sampler_name),
        'hr_sampler_name': req.sampler_name,
        'hr_scale': 0,  # overriden by hr_resize_x/y
        'hr_second_pass_steps': 0,  # 0 uses same num of steps as generation to refine details
        'hr_upscaler': req.upscaler_name,  # upscaler to use for highres fix
        'id_task': '',  # used by wrap_gradio_gpu_call for some sort of job id system
        'image_cfg_scale': 1.5,  # 1.5 is the default value used in SD.Next's UI
        'img2img_batch_files': [],
        'img2img_batch_inpaint_mask_dir': '',
        'img2img_batch_input_dir': '',
        'img2img_batch_output_dir': '',
        'img2img_batch_png_info_dir': '',  # (unsupported)
        'img2img_batch_png_info_props': [],  # (unsupported)
        'img2img_batch_use_png_info': False,  # (unsupported)
        'init_img_inpaint': image,
        'init_img_with_mask': None,
        'init_img': image,
        'init_images': [image],
        'init_mask_inpaint': mask,
        'inpaint_color_sketch_orig': None,
        'inpaint_color_sketch': None,
        'inpaint_full_res_padding': 0,
        'inpaint_full_res': False,
        'inpainting_fill': req.inpainting_fill if hasattr(req, 'inpainting_fill') else None,
        'inpainting_mask_invert': req.invert_mask if hasattr(req, 'invert_mask') else None,
        'latent_index': 0,
        'mask': mask,
        'mask_alpha': None,  # only used by webUI color sketch if init_img_with_mask isn't dict
        'mask_blur': 0,  # req.mask_blur,
        'mode': 4 if hasattr(req, 'is_inpaint') and req.is_inpaint else 0,  # we use 0 (img2img with init_img) & 4 (inpaint uploaded mask)
        'n_iter': req.batch_count,
        'negative_prompt': parse_prompt(req.negative_prompt),
        'outpath_grids': opts.outdir_grids or (opts.outdir_txt2img_grids if function_path == processing.StableDiffusionProcessingTxt2Img else opts.outdir_img2img_grids),
        'outpath_samples': opts.outdir_samples or (opts.outdir_txt2img_samples if function_path == processing.StableDiffusionProcessingTxt2Img else opts.outdir_img2img_samples),
        'override_settings': create_override_settings_dict([]),
        'override_settings_texts': [],
        'prompt_styles': 'None',  # Name of the saved style, with the string 'None' being the default
        'prompt': parse_prompt(req.prompt),
        'refiner_checkpoint': req.sd_model,
        'refiner_denoise_end': 1.0,
        'refiner_denoise_start': 0,
        'refiner_negative': parse_prompt(req.negative_prompt),
        'refiner_prompt': parse_prompt(req.prompt),
        'refiner_start': 0.0,
        'refiner_steps': 0,
        'refiner_switch_at': 1.0,
        'request': gr.Request(username="krita", headers={}, client={"host":"0.0.0.0"}),  # A1111 has an option to use the username from here, but doesn't use the rest of the request
        'resize_mode': req.resize_mode if hasattr(req, 'resize_mode') else 0,
        'restore_faces': req.restore_faces if hasattr(req, 'restore_faces') else False,
        'sampler_name': req.sampler_name,
        'sampler_index': get_sampler_index(req.sampler_name),
        'scale_by': 1.0,
        'seed_enable_extras': req.seed_enable_extras if hasattr(req, 'seed_enable_extras') else False,
        'seed_resize_from_h': req.seed_resize_from_h if hasattr(req, 'seed_resize_from_h') else height,
        'seed_resize_from_w': req.seed_resize_from_w if hasattr(req, 'seed_resize_from_w') else width,
        'seed': req.seed,
        'selected_scale_tab': 0,
        'sketch': None,
        'steps': req.steps,
        'subseed_strength': req.subseed_strength,
        'subseed': req.subseed,
        'tiling': req.tiling if hasattr(req, 'tiling') else False,
        'width': width,
    }

    matching_params = {}
    for param_name, param in inspect.signature(function_path).parameters.items():
        if param_name in params:
            matching_params[param_name] = params[param_name]

    return matching_params


@router.get("/config", response_model=ConfigResponse)
async def get_state():
    """Get information about backend API.

    Returns config from `krita_config.yaml`, other metadata,
    the path to the rendered image and image mask, etc.

    Returns:
        Dict: information.
    """
    opt = load_config().plugin
    prepare_backend(opt)

    sample_path = os.path.abspath(opt.sample_path)
    return {
        **opt.dict(),
        "sample_path": sample_path,
        "upscalers": [upscaler.name for upscaler in shared.sd_upscalers],
        "samplers": [sampler.name for sampler in modules.sd_samplers.samplers],
        "samplers_img2img": [
            sampler.name for sampler in modules.sd_samplers.samplers_for_img2img
        ],
        "scripts_txt2img": get_scripts_metadata(False),
        "scripts_img2img": get_scripts_metadata(True),
        "face_restorers": [model.name() for model in shared.face_restorers],
        "sd_models": modules.sd_models.checkpoint_tiles(),  # yes internal API has spelling error
        "sd_vaes": ["None", "Automatic" ] + (list(modules.sd_vae.vae_dict))
    }


@router.post("/txt2img", response_model=ImageResponse)
def f_txt2img(req: Txt2ImgRequest):
    """Post request for Txt2Img.

    Args:
        req (Txt2ImgRequest): Request.

    Returns:
        Dict: Outputs and info.
    """
    log.info(f"txt2img:\n{req}")

    opt = load_config().txt2img
    req = merge_default_config(req, opt)
    prepare_backend(req)

    script_ind, script, meta = get_script_info(req.script, False)
    args = process_script_args(script_ind, script, meta, req.script_args)

    width, height = sddebz_highres_fix(
        req.base_size,
        req.max_size,
        req.orig_width,
        req.orig_height,
        req.disable_sddebz_highres,
    )

    params = get_required_params(processing.StableDiffusionProcessingTxt2Img, req, height, width)

    def txt2img_setup():
        # Txt2Img calls
        p = processing.StableDiffusionProcessingTxt2Img(**params)
        p.scripts = modules.scripts.scripts_txt2img
        p.script_args = args

        if cmd_opts.enable_console_prompts:
            print(f"\ntxt2img: {parse_prompt(req.prompt)}", file = shared.progress_print_out)

        with closing(p):
            processed = modules.scripts.scripts_txt2img.run(p, *args)

            if processed is None:
                processed = processing.process_images(p)

        shared.total_tqdm.clear()

        generation_info_js = processed.js()
        if opts.samples_log_stdout:
            print(generation_info_js)

        return processed.images, generation_info_js, ""

    images, info, _ = wrap_gradio_gpu_call(txt2img_setup)()

    if images is None or len(images) < 1:
        log.warning("Interrupted!")
        return {"outputs": [], "info": info}

    if shared.opts.return_grid:
        if not req.include_grid and len(images) > 1 and script_ind == 0:
            images = images[1:]

    if not script or (width == images[0].width and height == images[0].height):
        log.info(
            f"img size: {images[0].width}x{images[0].height}, target: {req.orig_width}x{req.orig_height}"
        )
        images = [
            modules.images.resize_image(0, image, req.orig_width, req.orig_height)
            for image in images
        ]

    # save images for debugging/logging purposes
    if req.save_samples:
        output_paths = [
            save_img(image, opt.sample_path, filename=f"{int(time.time())}_{i}.png")
            for i, image in enumerate(images)
        ]
        log.info(f"saved: {output_paths}")

    images = [img_to_b64(image) for image in images]

    log.info(f"output sizes: {[len(i) for i in images]}")
    log.info(f"finished txt2img!")
    return {"outputs": images, "info": info}


@router.post("/img2img", response_model=ImageResponse)
def f_img2img(req: Img2ImgRequest):
    """Post request for Img2Img.

    Args:
        req (Img2ImgRequest): Request.

    Returns:
        Dict: Outputs and info.
    """
    log.info(f"img2img:\n{req.dict(exclude={'src_img', 'mask_img'})}")

    opt = load_config().img2img
    req = merge_default_config(req, opt)
    prepare_backend(req)

    script_ind, script, meta = get_script_info(req.script, True)
    args = process_script_args(script_ind, script, meta, req.script_args)

    image = b64_to_img(req.src_img)
    mask = (
        prepare_mask(b64_to_img(req.mask_img))
        if req.is_inpaint and req.mask_img is not None
        else None
    )

    orig_width, orig_height = image.size

    if script and script.title() == NAME_SCRIPT_UPSCALE:
        # in SD upscale mode, width & height determines tile size
        width = height = req.base_size
    else:
        width, height = sddebz_highres_fix(
            req.base_size,
            req.max_size,
            orig_width,
            orig_height,
            req.disable_sddebz_highres,
        )

    params = get_required_params(processing.StableDiffusionProcessingImg2Img, req, height, width, image, mask)

    def img2img_setup():
        # Img2Img Calls
        p = processing.StableDiffusionProcessingImg2Img(**params)
        p.scripts = modules.scripts.scripts_img2img
        p.script_args = args

        if shared.cmd_opts.enable_console_prompts:
            print(f"\nimg2img: {parse_prompt(req.prompt)}", file = shared.progress_print_out)

        if mask:
            p.extra_generation_params["Mask blur"] = 0

        with closing(p):
            processed = modules.scripts.scripts_img2img.run(p, *args)
            if processed is None:
                processed = processing.process_images(p)

        shared.total_tqdm.clear()

        generation_info_js = processed.js()
        if opts.samples_log_stdout:
            print(generation_info_js)

        return processed.images,  generation_info_js, ""  # Empty string because wrap_gradio_gpu_call hijacks the last return value of the function it wraps to add html info (actually another wrapper does, but it's the first wrapper that tells the second to do it)

    images, info, _ = wrap_gradio_gpu_call(img2img_setup)()

    if images is None or len(images) < 1:
        log.warning("Interrupted!")
        return {"outputs": [], "info": info}

    if shared.opts.return_grid:
        if not req.include_grid and len(images) > 1 and script_ind == 0:
            images = images[1:]
        # This is a workaround.
        if script and script.title() == NAME_SCRIPT_LOOPBACK and len(images) > 1:
            images = images[1:]

    # NOTE: this is a dumb assumption:
    # if size of image is different from size given to pipeline (after sbbedz fix)
    # then it must be intentional (i.e. SD Upscale/outpaint) so dont scale back
    if not script or (width == images[0].width and height == images[0].height):
        log.info(
            f"img Size: {images[0].width}x{images[0].height}, target: {orig_width}x{orig_height}"
        )
        images = [
            modules.images.resize_image(0, image, orig_width, orig_height)
            for image in images
        ]

    if req.is_inpaint:

        def apply_mask(img):
            """Mask inpaint using original mask, including alpha."""
            r, g, b = img.split()  # img2img/inpaint gives rgb image
            a = ImageOps.invert(mask) if req.invert_mask else mask
            return Image.merge("RGBA", (r, g, b, a))

        images = [apply_mask(x) for x in images]

    # save images for debugging/logging purposes
    if req.save_samples:
        output_paths = [
            save_img(image, opt.sample_path, filename=f"{int(time.time())}_{i}.png")
            for i, image in enumerate(images)
        ]
        log.info(f"saved: {output_paths}")

    images = [img_to_b64(image) for image in images]

    log.info(f"output sizes: {[len(i) for i in images]}")
    log.info(f"finished img2img!")
    return {"outputs": images, "info": info}


@router.post("/upscale", response_model=UpscaleResponse)
def f_upscale(req: UpscaleRequest):
    """Post request for upscaling.

    Args:
        req (UpscaleRequest): Request.

    Returns:
        Dict: Output.
    """
    log.info(f"upscale:\n{req.dict(exclude={'src_img'})}")

    opt = load_config().upscale
    req = merge_default_config(req, opt)
    prepare_backend(req)

    image = b64_to_img(req.src_img).convert("RGB")
    orig_width, orig_height = image.size

    upscaler_index = get_upscaler_index(req.upscaler_name)
    upscaler = shared.sd_upscalers[upscaler_index]

    if upscaler.name == "None":
        log.info(f"No upscaler selected, will do nothing")
        return

    if req.downscale_first:
        image = modules.images.resize_image(0, image, orig_width // 2, orig_height // 2)

    image = upscaler.scaler.upscale(image, upscaler.scale, upscaler.data_path)
    if req.save_samples:
        output_path = save_img(
            image, opt.sample_path, filename=f"{int(time.time())}.png"
        )
        log.info(f"saved: {output_path}")

    output = img_to_b64(image)
    log.info(f"output size: {len(output)}")
    log.info("finished upscale!")
    return {"output": output}


async def app_encryption_middleware(req: Request, call_next):
    """Used to decrypt/encrypt HTTP request body."""
    is_encrypted = "X-Encrypted-Body" in req.headers
    # only supported method now is XOR
    assert not is_encrypted or req.headers["X-Encrypted-Body"] == "XOR"
    if is_encrypted:
        key = get_encrypt_key()
        assert key is not None, "Unable to decrypt request without key."
        body = await req.body()
        body = bytewise_xor(body, key)
        # NOTE: FastAPI refuses to work with requests that have already been consumed idk why
        async def receive():
            return dict(type="http.request", body=body, more_body=False)

        req = Request(req.scope, receive, req._send)

    res: StreamingResponse = await call_next(req)
    if is_encrypted:
        res.headers["X-Encrypted-Body"] = req.headers["X-Encrypted-Body"]
        body = [bytewise_xor(chunk, key) async for chunk in res.body_iterator]
        res.body_iterator = iterate_in_threadpool(iter(body))
    return res
