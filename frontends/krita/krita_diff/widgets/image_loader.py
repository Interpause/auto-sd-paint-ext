from krita import QApplication, QFileDialog, QPixmap, QPushButton, QVBoxLayout, QHBoxLayout, Qt
from ..widgets import QLabel

class ImageLoaderLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super(ImageLoaderLayout, self).__init__(*args, **kwargs)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.importBtn = QPushButton('Import image')
        self.pasteBtn = QPushButton('Paste image')
        self.clearBtn = QPushButton('Clear')

        btnLayout = QHBoxLayout()
        btnLayout.addWidget(self.importBtn)
        btnLayout.addWidget(self.pasteBtn)

        self.addLayout(btnLayout)
        self.addWidget(self.clearBtn)
        self.addWidget(self.preview)

        self.importBtn.released.connect(self.load_image)
        self.pasteBtn.released.connect(self.paste_image)
        self.clearBtn.released.connect(self.clear_image)

    def disable(self):
        self.preview.setEnabled(False)
        self.importBtn.setEnabled(False)
        self.pasteBtn.setEnabled(False)
        self.clearBtn.setEnabled(False)

    def enable(self):
        self.preview.setEnabled(True)
        self.importBtn.setEnabled(True)
        self.pasteBtn.setEnabled(True)
        self.clearBtn.setEnabled(True)

    def load_image(self):
        self.clear_image()
        file_name, _ = QFileDialog.getOpenFileName(self.importBtn, 'Open File', '', 'Image Files (*.png *.jpg *.bmp)')
        if file_name:
            pixmap = QPixmap(file_name)

            if pixmap.width() > self.preview.width():
                pixmap = pixmap.scaledToWidth(self.preview.width(), Qt.SmoothTransformation)
                
            self.preview.setPixmap(pixmap)

    def paste_image(self):
        self.clear_image()
        self.preview.setPixmap(QApplication.clipboard().pixmap())

    def clear_image(self):
        self.preview.setPixmap(QPixmap())


        