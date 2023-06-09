import itertools
import os
import time
from typing import Union

from krita import (
    Document,
    Krita,
    Node,
    QImage,
    QColor,
    QPainter,
    QObject,
    QPixmap,
    QRect,
    Qt,
    QTimer,
    Selection,
    pyqtSignal
)

from .client import Client
from .config import Config
from .defaults import (
    ADD_MASK_TIMEOUT,
    ERR_NO_DOCUMENT,
    ETA_REFRESH_INTERVAL,
    EXT_CFG_NAME,
    STATE_INTERRUPT,
    STATE_RESET_DEFAULT,
    STATE_WAIT,
)
from .utils import (
    b64_to_img,
    find_optimal_selection_region,
    get_desc_from_resp,
    img_to_ba,
    save_img,
)


# Does it actually have to be a QObject?
# The only possible use I see is for event emitting
class Script(QObject):
    cfg: Config
    """config singleton"""
    client: Client
    """API client singleton"""
    status: str
    """Current status (shown in status bar)"""
    app: Krita
    """Krita's Application instance (KDE Application)"""
    doc: Document
    """Currently opened document if any"""
    node: Node
    """Currently selected layer in Krita"""
    selection: Selection
    """Selection region in Krita"""
    x: int
    """Left position of selection"""
    y: int
    """Top position of selection"""
    width: int
    """Width of selection"""
    height: int
    """Height of selection"""
    status_changed = pyqtSignal(str)
    config_updated = pyqtSignal()
    progress_update = pyqtSignal(object)

    def __init__(self):
        super(Script, self).__init__()
        # Persistent settings (should reload between Krita sessions)
        self.cfg = Config()
        # used for webUI scripts aka extensions not to be confused with their extensions
        self.ext_cfg = Config(name=EXT_CFG_NAME, model=None)
        self.client = Client(self.cfg, self.ext_cfg)
        self.client.status.connect(self.status_changed.emit)
        self.client.config_updated.connect(self.config_updated.emit)
        self.eta_timer = QTimer()
        self.eta_timer.setInterval(ETA_REFRESH_INTERVAL)
        self.eta_timer.timeout.connect(lambda: self.action_update_eta())
        self.progress_update.connect(lambda p: self.update_status_bar_eta(p))
        # keep track of inserted layers to prevent accidental usage as inpaint mask
        self._inserted_layers = []

    def restore_defaults(self, if_empty=False):
        """Restore to default config."""
        self.cfg.restore_defaults(not if_empty)
        self.ext_cfg.config.remove("")

        if not if_empty:
            self.status_changed.emit(STATE_RESET_DEFAULT)

    def update_status_bar_eta(self, progress):
        # print(progress)
        # NOTE: progress & eta_relative is bugged upstream when there is multiple jobs
        # so we use a substitute that seems to work
        state = progress["state"]
        cur_step = state["sampling_step"]
        total_steps = state["sampling_steps"]
        # doesnt take into account batch count
        num_jobs = len(self.client.long_reqs) - 1

        self.status_changed.emit(f"Step {cur_step}/{total_steps} ({num_jobs} in queue)")

    def update_selection(self):
        """Update references to key Krita objects as well as selection information."""
        self.app = Krita.instance()
        self.doc = self.app.activeDocument()

        # self.doc doesnt exist at app startup
        if not self.doc:
            self.status_changed.emit(ERR_NO_DOCUMENT)
            return

        self.node = self.doc.activeNode()
        self.selection = self.doc.selection()

        is_not_selected = (
            self.selection is None
            or self.selection.width() < 1
            or self.selection.height() < 1
        )
        if is_not_selected:
            self.x = 0
            self.y = 0
            self.width = self.doc.width()
            self.height = self.doc.height()
            self.selection = None  # for the two other cases of invalid selection
        else:
            self.x = self.selection.x()
            self.y = self.selection.y()
            self.width = self.selection.width()
            self.height = self.selection.height()

        assert (
            self.doc.colorDepth() == "U8"
        ), f'Only "8-bit integer/channel" supported, Document Color Depth: {self.doc.colorDepth()}'
        assert (
            self.doc.colorModel() == "RGBA"
        ), f'Only "RGB/Alpha" supported, Document Color Model: {self.doc.colorModel()}'

    def adjust_selection(self):
        """Adjust selection region to account for scaling and striding to prevent image stretch."""
        if self.selection is not None and self.cfg("fix_aspect_ratio", bool):
            x, y, width, height = find_optimal_selection_region(
                self.cfg("sd_base_size", int),
                self.cfg("sd_max_size", int),
                self.x,
                self.y,
                self.width,
                self.height,
                self.doc.width(),
                self.doc.height(),
            )

            self.x = x
            self.y = y
            self.width = width
            self.height = height

    def get_selection_image(self) -> QImage:
        """QImage of selection"""
        return QImage(
            self.doc.pixelData(self.x, self.y, self.width, self.height),
            self.width,
            self.height,
            QImage.Format_RGBA8888,
        ).rgbSwapped()

    def get_mask_image(self, using_official_api) -> Union[QImage, None]:
        """QImage of mask layer for inpainting"""
        if self.node.type() not in {"paintlayer", "filelayer"}:
            assert False, "Please select a valid layer to use as inpaint mask!"
        elif self.node in self._inserted_layers:
            assert False, "Selected layer was generated. Copy the layer if sure you want to use it as inpaint mask."

        mask = QImage(
            self.node.pixelData(self.x, self.y, self.width, self.height),
            self.width,
            self.height,
            QImage.Format_RGBA8888,
        )

        if using_official_api:
            # Official API requires a black and white mask.
            # Fastest way to do this: Convert to 1 channel alpha, tell it that
            # it's grayscale, convert that to RGBA.
            mask = mask.convertToFormat(QImage.Format_Alpha8)
            mask.reinterpretAsFormat(QImage.Format_Grayscale8)
            mask = mask.convertToFormat(QImage.Format_RGBA8888)

        return mask.rgbSwapped()

    def img_inserter(self, x, y, width, height, glayer=None):
        """Return frozen image inserter to insert images as new layer."""
        # Selection may change before callback, so freeze selection region
        has_selection = self.selection is not None

        def create_layer(name: str):
            """Create new layer in document or group"""
            layer = self.doc.createNode(name, "paintLayer")
            parent = self.doc.rootNode()
            if glayer:
                glayer.addChildNode(layer, None)
            else:
                parent.addChildNode(layer, None)
            return layer
            
        def insert(layer_name, enc):
            nonlocal x, y, width, height, has_selection
            print(f"inserting layer {layer_name}")
            print(f"data size: {len(enc)}")

            # QImage.Format_RGB32 (4) is default format after decoding image
            # QImage.Format_RGBA8888 (17) is format used in Krita tutorial
            # both are compatible, & converting from 4 to 17 required a RGB swap
            # Likewise for 5 & 18 (their RGBA counterparts)
            image = b64_to_img(enc)
            print(
                f"image created: {image}, {image.width()}x{image.height()}, depth: {image.depth()}, format: {image.format()}"
            )

            # NOTE: Scaling is usually done by backend (although I am reconsidering this)
            # The scaling here is for SD Upscale or Upscale on a selection region rather than whole image
            # Image won't be scaled down ONLY if there is no selection; i.e. selecting whole image will scale down,
            # not selecting anything won't scale down, leading to the canvas being resized afterwards
            if has_selection and (image.width() != width or image.height() != height):
                print(f"Rescaling image to selection: {width}x{height}")
                image = image.scaled(
                    width, height, transformMode=Qt.SmoothTransformation
                )

            # Resize (not scale!) canvas if image is larger (i.e. outpainting or Upscale was used)
            if image.width() > self.doc.width() or image.height() > self.doc.height():
                # NOTE:
                # - user's selection will be partially ignored if image is larger than canvas
                # - it is complex to scale/resize the image such that image fits in the newly scaled selection
                # - the canvas will still be resized even if the image fits after transparency masking
                print("Image is larger than canvas! Resizing...")
                new_width, new_height = self.doc.width(), self.doc.height()
                if image.width() > self.doc.width():
                    x, width, new_width = 0, image.width(), image.width()
                if image.height() > self.doc.height():
                    y, height, new_height = 0, image.height(), image.height()
                self.doc.resizeImage(0, 0, new_width, new_height)

            ba = img_to_ba(image)
            layer = create_layer(layer_name)
            # layer.setColorSpace() doesn't pernamently convert layer depth etc...

            # Don't fail silently for setPixelData(); fails if bit depth or number of channels mismatch
            size = ba.size()
            expected = layer.pixelData(x, y, width, height).size()
            assert expected == size, f"Raw data size: {size}, Expected size: {expected}"

            print(f"inserting at x: {x}, y: {y}, w: {width}, h: {height}")
            layer.setPixelData(ba, x, y, width, height)
            self._inserted_layers.append(layer)

            return layer

        return insert
    
    def check_controlnet_enabled(self):
        for i in range(len(self.cfg("controlnet_unit_list", "QStringList"))):
            if self.cfg(f"controlnet{i}_enable", bool):
                return True
            
    def get_controlnet_input_images(self, selected):
        input_images = dict()

        for i in range(len(self.cfg("controlnet_unit_list", "QStringList"))):    
            if self.cfg(f"controlnet{i}_enable", bool):
                input_image = b64_to_img(self.cfg(f"controlnet{i}_input_image", str)) if \
                    self.cfg(f"controlnet{i}_input_image", str) else selected
                    
                input_images.update({f"{i}": input_image})

        return input_images

    def apply_txt2img(self):
        # freeze selection region
        controlnet_enabled = self.check_controlnet_enabled()
        glayer = self.doc.createGroupLayer("Unnamed Group")
        self.doc.rootNode().addChildNode(glayer, None)
        insert = self.img_inserter(
            self.x, self.y, self.width, self.height, glayer
        )
        mask_trigger = self.transparency_mask_inserter()

        def cb(response):
            if len(self.client.long_reqs) == 1:  # last request
                self.eta_timer.stop()
            assert response is not None, "Backend Error, check terminal"
            #response key varies for official api used for controlnet
            outputs = response["outputs"] if not controlnet_enabled else response["images"]
            glayer_name, layer_names = get_desc_from_resp(response, "txt2img")
            layers = [
                insert(name if name else f"txt2img {i + 1}", output)
                for output, name, i in zip(outputs, layer_names, itertools.count())
            ]
            if self.cfg("hide_layers", bool):
                for layer in layers[:-1]:
                    layer.setVisible(False)
            if glayer:
                glayer.setName(glayer_name)
            self.doc.refreshProjection()
            mask_trigger(layers)

        self.eta_timer.start(ETA_REFRESH_INTERVAL)

        if controlnet_enabled:
            sel_image = self.get_selection_image()
            self.client.post_official_api_txt2img(
                cb, self.width, self.height, self.selection is not None, 
                self.get_controlnet_input_images(sel_image)
            )
        else:
            self.client.post_txt2img(
                cb, self.width, self.height, self.selection is not None
            )

    def apply_img2img(self, is_inpaint):
        controlnet_enabled = self.check_controlnet_enabled()

        mask_trigger = self.transparency_mask_inserter()
        mask_image = self.get_mask_image(controlnet_enabled) if is_inpaint else None
        glayer = self.doc.createGroupLayer("Unnamed Group")
        self.doc.rootNode().addChildNode(glayer, None)
        insert = self.img_inserter(
            self.x, self.y, self.width, self.height, glayer
        )

        path = os.path.join(self.cfg("sample_path", str), f"{int(time.time())}.png")
        mask_path = os.path.join(
            self.cfg("sample_path", str), f"{int(time.time())}_mask.png"
        )
        if is_inpaint and mask_image is not None:
            if self.cfg("save_temp_images", bool):
                save_img(mask_image, mask_path)
            # auto-hide mask layer before getting selection image
            self.node.setVisible(False)
            self.controlnet_transparency_mask_inserter(glayer, mask_image)
            self.doc.refreshProjection()

        sel_image = self.get_selection_image()
        if self.cfg("save_temp_images", bool):
            save_img(sel_image, path)

        def cb(response):
            def cb_upscale(upscale_response):
                if len(self.client.long_reqs) == 1:  # last request
                    self.eta_timer.stop()
                assert response is not None, "Backend Error, check terminal"

                outputs = upscale_response["images"]
                layer_name_prefix = "inpaint" if is_inpaint else "img2img"
                glayer_name, layer_names = get_desc_from_resp(response, layer_name_prefix)
                layers = [
                    insert(name if name else f"{layer_name_prefix} {i + 1}", output)
                    for output, name, i in zip(outputs, layer_names, itertools.count())
                ]
                if self.cfg("hide_layers", bool):
                    for layer in layers[:-1]:
                        layer.setVisible(False)
                if glayer:
                    glayer.setName(glayer_name)
                self.doc.refreshProjection()

            if len(self.client.long_reqs) == 1:  # last request
                self.eta_timer.stop()
            assert response is not None, "Backend Error, check terminal"

            outputs = response["outputs"] if not controlnet_enabled else response["images"]

            if controlnet_enabled: 
                if min(self.width,self.height) > self.cfg("sd_base_size", int) \
                    or max(self.width,self.height) > self.cfg("sd_max_size", int):
                    # this only handles with base/max size enabled
                    self.client.post_official_api_upscale_postprocess(
                        cb_upscale, outputs, self.width, self.height)
                else:
                    # passing response directly to the callback works fine
                    cb_upscale(response) 
                return

            layer_name_prefix = "inpaint" if is_inpaint else "img2img"
            glayer_name, layer_names = get_desc_from_resp(response, layer_name_prefix)
            layers = [
                insert(name if name else f"{layer_name_prefix} {i + 1}", output)
                for output, name, i in zip(outputs, layer_names, itertools.count())
            ]
            if self.cfg("hide_layers", bool):
                for layer in layers[:-1]:
                    layer.setVisible(False)
            if glayer:
                glayer.setName(glayer_name)
            self.doc.refreshProjection()
            # dont need transparency mask for inpaint mode
            if not is_inpaint:
                mask_trigger(layers)

        self.eta_timer.start()
        if controlnet_enabled:
            if is_inpaint:
                self.client.post_official_api_inpaint(
                    cb, sel_image, mask_image, self.width, self.height, self.selection is not None,
                    self.get_controlnet_input_images(sel_image))
            else:
                self.client.post_official_api_img2img(
                    cb, sel_image, self.width, self.height, self.selection is not None,
                    self.get_controlnet_input_images(sel_image))
        else:
            method = self.client.post_inpaint if is_inpaint else self.client.post_img2img
            method(
                cb,
                sel_image,
                mask_image,  # is unused by backend in img2img mode
                self.selection is not None,
            )
    
    def controlnet_transparency_mask_inserter(self, glayer, mask_image):
        orig_selection = self.selection.duplicate() if self.selection else None
        create_mask = self.cfg("create_mask_layer", bool)
        add_mask_action = self.app.action("add_new_transparency_mask")
        merge_mask_action = self.app.action("flatten_layer")

        if orig_selection:
            sx = orig_selection.x()
            sy = orig_selection.y()
            sw = orig_selection.width()
            sh = orig_selection.height()
        else:
            sx = 0
            sy = 0
            sw = self.doc.width()
            sh = self.doc.height()
        # must convert mask to single channel format
        gray_mask = mask_image.convertToFormat(QImage.Format_Grayscale8)
        
        w = gray_mask.width()
        h = gray_mask.height()
        
        # crop mask to the actual selection side
        # int division should end up on the right side of rounding here
        crop_rect = QRect((w - sw)/2,(h - sh)/2, sw, sh)
        crop_mask = gray_mask.copy(crop_rect)

        mask_ba = img_to_ba(crop_mask)

        mask_selection = Selection()
        mask_selection.setPixelData(mask_ba, sx, sy, sw, sh)

        self.doc.setActiveNode(glayer)
        self.doc.setSelection(mask_selection)
        self.doc.waitForDone() # deals with race condition?
        add_mask_action.trigger()
        self.doc.waitForDone()
        self.doc.setSelection(orig_selection)

    def apply_controlnet_preview_annotator(self, preview_label): 
        unit = self.cfg("controlnet_unit", str)
        if self.cfg(f"controlnet{unit}_input_image"):
            image = b64_to_img(self.cfg(f"controlnet{unit}_input_image"))
        else:
            image = self.get_selection_image()    

        def cb(response):
            assert response is not None, "Backend Error, check terminal"
            output = response["images"][0]
            pixmap = QPixmap.fromImage(b64_to_img(output))

            if pixmap.width() > preview_label.width():
                pixmap = pixmap.scaledToWidth(preview_label.width(), Qt.SmoothTransformation)
            preview_label.setPixmap(pixmap)

        self.client.post_controlnet_preview(cb, image)

    def apply_simple_upscale(self):
        insert = self.img_inserter(self.x, self.y, self.width, self.height)
        sel_image = self.get_selection_image()

        path = os.path.join(self.cfg("sample_path", str), f"{int(time.time())}.png")
        if self.cfg("save_temp_images", bool):
            save_img(sel_image, path)

        def cb(response):
            assert response is not None, "Backend Error, check terminal"
            output = response["output"]
            insert(f"upscale", output)
            self.doc.refreshProjection()

        self.client.post_upscale(cb, sel_image)

    def transparency_mask_inserter(self):
        """Mask out extra regions due to adjust_selection()."""
        orig_selection = self.selection.duplicate() if self.selection else None
        create_mask = self.cfg("create_mask_layer", bool)

        add_mask_action = self.app.action("add_new_transparency_mask")
        merge_mask_action = self.app.action("flatten_layer")

        # This function is recursive to workaround race conditions when calling Krita's actions
        def add_mask(layers: list, cur_selection):
            if len(layers) < 1:
                self.doc.setSelection(cur_selection)  # reset to current selection
                return
            layer = layers.pop()

            orig_visible = layer.visible()
            orig_name = layer.name()

            def restore():
                # assume newly flattened layer is active
                result = self.doc.activeNode()
                result.setVisible(orig_visible)
                result.setName(orig_name)

                add_mask(layers, cur_selection)

            layer.setVisible(True)
            self.doc.setActiveNode(layer)
            self.doc.setSelection(orig_selection)
            add_mask_action.trigger()
                
            if create_mask:
                # collapse transparency mask by default
                layer.setCollapsed(True)
                layer.setVisible(orig_visible)
                QTimer.singleShot(
                    ADD_MASK_TIMEOUT, lambda: add_mask(layers, cur_selection)
                )
            else:
                # flatten transparency mask into layer
                merge_mask_action.trigger()
                QTimer.singleShot(ADD_MASK_TIMEOUT, lambda: restore())

        def trigger_mask_adding(layers: list):
            layers = layers[::-1]  # causes final active layer to be the top one

            def handle_mask():
                cur_selection = self.selection.duplicate() if self.selection else None
                add_mask(layers, cur_selection)

            QTimer.singleShot(ADD_MASK_TIMEOUT, lambda: handle_mask())

        return trigger_mask_adding

    # Actions
    def action_txt2img(self):
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        if not self.doc:
            return
        self.adjust_selection()
        self.apply_txt2img()

    def action_img2img(self):
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        if not self.doc:
            return
        self.adjust_selection()
        self.apply_img2img(False)

    def action_sd_upscale(self):
        assert False, "disabled"
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        self.apply_img2img(mode=2)

    def action_inpaint(self):
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        if not self.doc:
            return
        self.adjust_selection()
        self.apply_img2img(True)

    def action_simple_upscale(self):
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        if not self.doc:
            return
        self.apply_simple_upscale()

    def action_update_config(self):
        """Update certain config/state from the backend."""
        self.client.get_config()
            
    def action_update_controlnet_config(self):
        """Update controlnet config from the backend."""
        self.client.get_controlnet_config()

    def action_preview_controlnet_annotator(self, preview_label):
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        if not self.doc:
            return
        self.adjust_selection()
        self.apply_controlnet_preview_annotator(preview_label)

            
    def action_update_controlnet_config(self):
        """Update controlnet config from the backend."""
        self.client.get_controlnet_config()

    def action_preview_controlnet_annotator(self, preview_label):
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        if not self.doc:
            return
        self.adjust_selection()
        self.apply_controlnet_preview_annotator(preview_label)

    def action_interrupt(self):
        def cb(resp=None):
            self.status_changed.emit(STATE_INTERRUPT)

        self.client.post_interrupt(cb)

    def action_update_eta(self):
        self.client.get_progress(self.progress_update.emit)


script = Script()
