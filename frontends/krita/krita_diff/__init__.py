from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita

from .docker import create_docker
from .extension import SDPluginExtension
from .pages import (
    ConfigTabWidget,
    Img2ImgTabWidget,
    InpaintTabWidget,
    SDCommonWidget,
    Txt2ImgTabWidget,
    UpscaleTabWidget,
)

# TODO:
# - split each tab into its own Docker
# - by default, dock all the tabs onto each other except quick config
# - see https://scripting.krita.org/lessons/docker-widgets
# - Might want to seriously consider drawing the line on what is done by backend/frontend

instance = Krita.instance()
instance.addExtension(SDPluginExtension(instance))
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_sdcommon",
        DockWidgetFactoryBase.DockLeft,
        create_docker(SDCommonWidget),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_txt2img",
        DockWidgetFactoryBase.DockLeft,
        create_docker(Txt2ImgTabWidget),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_img2img",
        DockWidgetFactoryBase.DockLeft,
        create_docker(Img2ImgTabWidget),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_inpaint",
        DockWidgetFactoryBase.DockLeft,
        create_docker(InpaintTabWidget),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_upscale",
        DockWidgetFactoryBase.DockLeft,
        create_docker(UpscaleTabWidget),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_config",
        DockWidgetFactoryBase.DockLeft,
        create_docker(ConfigTabWidget),
    )
)
