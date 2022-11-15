from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita

from .docker import SDPluginDocker
from .extension import SDPluginExtension

instance = Krita.instance()
instance.addExtension(SDPluginExtension(instance))
instance.addDockWidgetFactory(
    DockWidgetFactory("krita_diff", DockWidgetFactoryBase.DockLeft, SDPluginDocker)
)
