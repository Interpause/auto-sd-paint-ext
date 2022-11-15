# UI Changelog

## 2022-11-15

- Scripts/features that increase the image size (Simple upscaling, SD upscaling, Outpaint Mk 2, etc) will now expand the canvas when image generation is complete **only if** _there is no active selection_.
  - If there is a selection, the image will be scaled to fit the selection region.
  - Using Ctrl+A to select the entire image is considered an active selection!
- **UI Overhaul**: A few miscellaneous changes with some big ones:
  - All tabs are now their own dockers to allow more flexibility in arranging.

## 2022-11-08

- Inpainting is finally 100% fixed! No more weird borders. Blur works properly.
- Inpainting Full Resolution and Mask Blur were deemed obsolete and removed.
  - See <https://github.com/Interpause/auto-sd-paint-ext/wiki/Usage-Guide#inpainting> on better ways to do so.

## 2022-10-31

- Moved base size/max size & some other quick config options based on user feedback.

## 2022-10-25

- Will now save previous tab user was on.
- Fixed seed being truncated to 32-bit int.
- Prevent sending image generation request when cannot connect to backend.

## 2022-10-24

- UI no longer freezes when generating images or network activity like getting backend config
  - Pressing "start xxx" multiple times will queue generation requests on the backend
  - Will not mess with the current selection region or layer when inserting images once done

## 2022-10-21

- No need to manually hide inpainting layer anymore; It will be auto-hidden.
- Color correction can be toggled separately for img2img/inpainting.
- Status bar:
  - In middle of page to be more visible even when scrolling.
  - Warning when using features with no document open.
- Inpaint is now the default tab.
