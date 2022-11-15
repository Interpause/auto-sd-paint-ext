# auto-sd-paint-ext

Formerly known as `auto-sd-krita`.

> Extension for AUTOMATIC1111's webUI with Krita Plugin (other drawing studios soon?)

Outdated demo | New UI (TODO: demo image)
--- | ---
![demo image](https://user-images.githubusercontent.com/42513874/194701722-e7a3f7eb-be4a-4f43-93a5-480835c9260f.jpg) | ![demo image 2](https://user-images.githubusercontent.com/42513874/199507299-66729f9b-3581-43a3-b5f4-57eb90b8f981.png)

Why use this?

- Optimized workflow (txt2img, img2img, inpaint, outpaint, upscale) & UI design.
- Only drawing studio plugin that exposes the Script API.
- Easily create/save profiles (prompts, samplers, model, etc used).
- Some of the above isn't actually implemented yet.

## Quick Jump

- Full Installation & Workflow Tutorial Video! (Coming Soon...)
- [Installation Guide](https://github.com/Interpause/auto-sd-paint-ext/wiki/Install-Guide)
- [Usage Guide](https://github.com/Interpause/auto-sd-paint-ext/wiki/Usage-Guide)
  - [Step by Step Guide to Better Inpainting](https://github.com/Interpause/auto-sd-paint-ext/wiki/Usage-Guide#inpainting-step-by-step)
- [Update Guide](https://github.com/Interpause/auto-sd-paint-ext/wiki/Update-Guide)
- [Features](https://github.com/Interpause/auto-sd-paint-ext/wiki/Features)
- [TODO](https://github.com/Interpause/auto-sd-paint-ext/wiki/TODO)
- [Contribution Guide](https://github.com/Interpause/auto-sd-paint-ext/wiki/Contribution-Guide)

(Outdated) Usage & Workflow Demo:

[![Youtube Video](http://img.youtube.com/vi/nP8MuRwcDN8/0.jpg)](https://youtu.be/nP8MuRwcDN8 "Inpaint like a pro with Stable Diffusion! auto-sd-krita workflow guide")

### Differences from Video

- All webUI scripts have been tested to work!
  - SD Upscale, Outpainting Mk 2, Img2Img Alt, etc
- Inpainting experience is better
  - Inpaint mask is auto-hidden
  - Better mask blur & inpaint full resolution technique than webUI
- UI no longer freezes during image update
- UI has been improved, takes up less space
- Error messages have been improved

## Breaking Changes

- The URL is different now, so reset "Backend URL" to default under the Config tab.
- It is now an AUTOMATIC1111 extension.
  - Do <https://github.com/Interpause/auto-sd-krita/wiki/Quick-Switch-Using-Existing-AUTOMATIC1111-Install> in reverse for a quick fix.
- `krita_config.yaml` was renamed to `auto-sd-paint-ext-backend.yaml`.

## FAQ

Q: How does the base_size, max_size system work?

A:

It is an alternative to AUTO's highres fix that works for all modes, not just txt2img.

The selection will be resized such that the shorter dimension is base_size. However, if the aforementioned resize causes the longer dimension to exceed max_size, the shorter dimension will be resized to less than base_size. Setting base_size and max_size higher can be used to generate higher resolution images (along with their issues), essentially **disabling the system**, _though it might make sense for img2img mode_.

This is actually smarter than the builtin highres fix + firstphase width/height system. Thank the original plugin writer, @sddebz, for writing this.

<hr/>

Q: Outpainting tab?

A:
While the outpainting tab is still WIP, the outpainting scripts (under img2img tab) works perfectly fine! Alternatively, if you want more control over outpainting, you can:

1. Expand the canvas
2. Scribble in the newly added blank area
3. img2img on the blank area + some of the image

<hr/>

Q: Is the model loaded into memory twice?

A: No, it shares the same backend. Both the Krita plugin and webUI can be used concurrently.

<hr/>

Q: How can you commit to updating regularly?

A: It is easy for me.

<hr/>

Q: Will it work with other Krita plugin backends?

A: Unfortunately no, all plugins so far have different APIs. The official API is coming soon though...

## UI Changelog

### 2022-11-15

- Scripts/features that increase the image size (Simple upscaling, SD upscaling, Outpaint Mk 2, etc) will now expand the canvas when image generation is complete **only if** _there is no active selection_.
  - If there is a selection, the image will be scaled to fit the selection region.
  - Using Ctrl+A to select the entire image is considered an active selection!

### 2022-11-08

- Inpainting is finally 100% fixed! No more weird borders. Blur works properly.
- Inpainting Full Resolution and Mask Blur were deemed obsolete and removed.
  - See <https://github.com/Interpause/auto-sd-paint-ext/wiki/Usage-Guide#inpainting> on better ways to do so.

### 2022-10-31

- Moved base size/max size & some other quick config options based on user feedback.

### 2022-10-25

- Will now save previous tab user was on.
- Fixed seed being truncated to 32-bit int.
- Prevent sending image generation request when cannot connect to backend.

### 2022-10-24

- UI no longer freezes when generating images or network activity like getting backend config
  - Pressing "start xxx" multiple times will queue generation requests on the backend
  - Will not mess with the current selection region or layer when inserting images once done

### 2022-10-21

- No need to manually hide inpainting layer anymore; It will be auto-hidden.
- Color correction can be toggled separately for img2img/inpainting.
- Status bar:
  - In middle of page to be more visible even when scrolling.
  - Warning when using features with no document open.
- Inpaint is now the default tab.

## Credits

- [@sddebz](https://github.com/sddebz) for writing the original backend API and Krita plugin while keeping the Gradio webUI functionality intact.

## License

MIT for the Krita Plugin backend server & frontend plugin. Code has been nearly completely rewritten compared to original plugin by now.
