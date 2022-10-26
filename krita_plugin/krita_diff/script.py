import os
import time

from krita import Document, Krita, Node, QImage, QObject, QTimer, Selection, pyqtSignal

from .client import Client
from .config import Config
from .defaults import (
    ADD_MASK_TIMEOUT,
    ERR_NO_DOCUMENT,
    EXT_CFG_NAME,
    STATE_IMG2IMG,
    STATE_INIT,
    STATE_INPAINT,
    STATE_READY,
    STATE_RESET_DEFAULT,
    STATE_TXT2IMG,
    STATE_UPSCALE,
    STATE_URLERROR,
    STATE_WAIT,
)
from .utils import (
    b64_to_img,
    create_layer,
    find_optimal_selection_region,
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

    def __init__(self):
        super(Script, self).__init__()
        # Persistent settings (should reload between Krita sessions)
        self.cfg = Config()
        # used for webUI scripts aka extensions not to be confused with their extensions
        self.ext_cfg = Config(name=EXT_CFG_NAME, defaults=None)
        self.client = Client(self.cfg, self.ext_cfg)
        self.client.status.connect(self.status_changed.emit)

    def restore_defaults(self, if_empty=False):
        """Restore to default config."""
        self.cfg.restore_defaults(not if_empty)

        if not if_empty:
            self.status_changed.emit(STATE_RESET_DEFAULT)

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
        else:
            self.x = self.selection.x()
            self.y = self.selection.y()
            self.width = self.selection.width()
            self.height = self.selection.height()

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

    def get_mask_image(self) -> QImage:
        """QImage of mask layer"""
        return QImage(
            self.node.pixelData(self.x, self.y, self.width, self.height),
            self.width,
            self.height,
            QImage.Format_RGBA8888,
        ).rgbSwapped()

    def update_config(self):
        """Update certain config/state from the backend."""
        return self.client.get_config()

    def img_inserter(self, x, y, width, height):
        """Return frozen image inserter to insert images as new layer."""
        # Selection may change before callback, so freeze selection region
        def insert(layer_name, enc):
            image = b64_to_img(enc)
            ba = img_to_ba(image)
            layer = create_layer(self.doc, layer_name)
            layer.setPixelData(ba, x, y, width, height)
            return layer

        return insert

    def apply_txt2img(self):
        # freeze selection region
        insert = self.img_inserter(self.x, self.y, self.width, self.height)
        mask_trigger = self.transparency_mask_inserter()

        def cb(response):
            assert response is not None, "Backend Error, check terminal"
            outputs = response["outputs"]
            layers = [
                insert(f"txt2img {i + 1}", output) for i, output in enumerate(outputs)
            ]
            self.doc.refreshProjection()
            mask_trigger(layers)
            self.status_changed.emit(STATE_TXT2IMG)

        self.client.post_txt2img(
            cb, self.width, self.height, self.selection is not None
        )

    def apply_img2img(self, mode):
        insert = self.img_inserter(self.x, self.y, self.width, self.height)
        mask_trigger = self.transparency_mask_inserter()
        mask_image = self.get_mask_image()

        path = os.path.join(self.cfg("sample_path", str), f"{int(time.time())}.png")
        mask_path = os.path.join(
            self.cfg("sample_path", str), f"{int(time.time())}_mask.png"
        )
        if mode == 1:
            if self.cfg("save_temp_images", bool):
                save_img(mask_image, mask_path)
            # auto-hide mask layer before getting selection image
            self.node.setVisible(False)
            self.doc.refreshProjection()

        sel_image = self.get_selection_image()
        if self.cfg("save_temp_images", bool):
            save_img(sel_image, path)

        def cb(response):
            assert response is not None, "Backend Error, check terminal"

            outputs = response["outputs"]
            layer_name_prefix = (
                "inpaint" if mode == 1 else "sd upscale" if mode == 2 else "img2img"
            )
            layers = [
                insert(f"{layer_name_prefix} {i + 1}", output)
                for i, output in enumerate(outputs)
            ]
            self.doc.refreshProjection()
            if mode == 0:
                mask_trigger(layers)
                self.status_changed.emit(STATE_IMG2IMG)
            else:  # dont need transparency mask for inpaint mode
                self.status_changed.emit(STATE_INPAINT)

        method = self.client.post_inpaint if mode == 1 else self.client.post_img2img
        method(
            cb,
            sel_image,
            mask_image,  # is unused by backend in img2img mode
            self.selection is not None,
        )

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
            self.status_changed.emit(STATE_UPSCALE)

        self.client.post_upscale(cb, sel_image)

    def transparency_mask_inserter(self):
        """Mask out extra regions due to adjust_selection()."""
        orig_selection = self.selection.duplicate() if self.selection else None

        def add_mask(layers):
            self.doc.waitForDone()
            cur_selection = self.selection
            cur_layer = self.doc.activeNode()
            for layer in layers:
                self.doc.setActiveNode(layer)
                self.doc.setSelection(orig_selection)
                self.app.action("add_new_transparency_mask").trigger()
            self.doc.setSelection(cur_selection)  # reset to current selection
            self.doc.setActiveNode(cur_layer)  # reset to current layer

        def trigger_mask_adding(layers):
            if self.cfg("create_mask_layer", bool):
                # need timeout to ensure layer exists first else crash
                QTimer.singleShot(ADD_MASK_TIMEOUT, lambda: add_mask(layers))

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
        self.apply_img2img(mode=0)

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
        self.apply_img2img(mode=1)

    def action_simple_upscale(self):
        self.status_changed.emit(STATE_WAIT)
        self.update_selection()
        if not self.doc:
            return
        self.apply_simple_upscale()


script = Script()
