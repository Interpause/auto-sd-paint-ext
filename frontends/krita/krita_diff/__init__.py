from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita

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
        create_docker(SDCommonPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_txt2img",
        DockWidgetFactoryBase.DockLeft,
        create_docker(Txt2ImgPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_img2img",
        DockWidgetFactoryBase.DockLeft,
        create_docker(Img2ImgPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_inpaint",
        DockWidgetFactoryBase.DockLeft,
        create_docker(InpaintPage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_upscale",
        DockWidgetFactoryBase.DockLeft,
        create_docker(UpscalePage),
    )
)
instance.addDockWidgetFactory(
    DockWidgetFactory(
        "krita_diff_config",
        DockWidgetFactoryBase.DockLeft,
        create_docker(ConfigPage),
    )
)
