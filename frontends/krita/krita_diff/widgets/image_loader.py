from krita import QWidget, QFileDialog, QPixmap, QPushButton, QVBoxLayout, QHBoxLayout, Qt
from ..widgets import QLabel

class ImageLoaderLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super(ImageLoaderLayout, self).__init__(*args, **kwargs)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.importBtn = QPushButton('Import image')
        self.clearBtn = QPushButton('Clear')

        btnLayout = QHBoxLayout()
        btnLayout.addWidget(self.importBtn)
        btnLayout.addWidget(self.clearBtn)

        self.addLayout(btnLayout)
        self.addWidget(self.preview)

        self.importBtn.released.connect(self.load_image)
        self.clearBtn.released.connect(self.clear_image)

    def disable(self):
        self.preview.setEnabled(False)
        self.importBtn.setEnabled(False)
        self.clearBtn.setEnabled(False)

    def enable(self):
        self.preview.setEnabled(True)
        self.importBtn.setEnabled(True)
        self.clearBtn.setEnabled(True)

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self.importBtn, 'Open File', '', 'Image Files (*.png *.jpg *.bmp)')
        if file_name:
            pixmap = QPixmap(file_name)

            if pixmap.width() > self.preview.width():
                pixmap = pixmap.scaledToWidth(self.preview.width(), Qt.SmoothTransformation)
                
            self.preview.setPixmap(pixmap)

    def clear_image(self):
        self.preview.setPixmap(QPixmap())


        