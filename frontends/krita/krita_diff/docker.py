from krita import DockWidget, QScrollArea

from .script import script
from .style import style


def create_docker(page):
    class Docker(DockWidget):
        def __init__(self, *args, **kwargs):
            super(Docker, self).__init__(*args, **kwargs)
            self.setWindowTitle(page.name)
            self.create_interface()
            self.update_interface()
            self.connect_interface()
            self.setWidget(self.widget)

        def create_interface(self):
            self.page_widget = page()
            self.widget = QScrollArea()
            self.widget.setStyleSheet(style)
            self.widget.setWidget(self.page_widget)
            self.widget.setWidgetResizable(True)

        def update_interface(self):
            self.page_widget.cfg_init()

        def connect_interface(self):
            self.page_widget.cfg_connect()
            script.config_updated.connect(lambda: self.update_interface())

        def canvasChanged(self, canvas):
            pass

    return Docker
