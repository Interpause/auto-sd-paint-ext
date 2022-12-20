from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita

from .defaults import (
    TAB_CONFIG,
    TAB_IMG2IMG,
    TAB_INPAINT,
    TAB_SDCOMMON,
    TAB_TXT2IMG,
    TAB_UPSCALE,
)
from .docker import create_docker
from .extension import SDPluginExtension
from .pages import (
    ConfigPage,
    Img2ImgPage,
    InpaintPage,
    SDCommonPage,
    Txt2ImgPage,
    UpscalePage,
)
from .script import script
from .utils import reset_docker_layout

instance = Krita.instance()
instance.addExtension(SDPluginExtension(instance))
instance.addDockWidgetFactory(
    DockWidgetFactory(
        TAB_SDCOMMON,
        DockWidgetFactoryBase.DockLeft,
        create_docker(SDCommonPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        TAB_TXT2IMG,
        DockWidgetFactoryBase.DockLeft,
        create_docker(Txt2ImgPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        TAB_IMG2IMG,
        DockWidgetFactoryBase.DockLeft,
        create_docker(Img2ImgPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        TAB_INPAINT,
        DockWidgetFactoryBase.DockLeft,
        create_docker(InpaintPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        TAB_UPSCALE,
        DockWidgetFactoryBase.DockLeft,
        create_docker(UpscalePage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        TAB_CONFIG,
        DockWidgetFactoryBase.DockLeft,
        create_docker(ConfigPage),
    )
)


# dumb workaround to ensure its only created once
if script.cfg("first_setup", bool):
    instance.notifier().windowCreated.connect(reset_docker_layout)
    script.cfg.set("first_setup", False)
