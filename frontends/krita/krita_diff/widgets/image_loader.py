from krita import QWidget, QFileDialog, QPixmap, QPushButton, QVBoxLayout, QHBoxLayout, Qt
from ..widgets import QLabel

class ImageLoader(QWidget):
    def __init__(self, *args, **kwargs):
        super(ImageLoader, self).__init__(*args, **kwargs)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.importBtn = QPushButton('Import image')
        self.clearBtn = QPushButton('Clear')

        btnLayout = QHBoxLayout()
        btnLayout.addWidget(self.importBtn)
        btnLayout.addWidget(self.clearBtn)

        layout = QVBoxLayout()
        layout.addLayout(btnLayout)
        layout.addWidget(self.preview)
        self.setLayout(layout)

        self.importBtn.released.connect(self.load_image)
        self.clearBtn.released.connect(self.clear_image)

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'Image Files (*.png *.jpg *.bmp)')
        if file_name:
            pixmap = QPixmap(file_name)

            if pixmap.width() > self.preview.width():
                pixmap = pixmap.scaledToWidth(self.preview.width(), Qt.SmoothTransformation)
                
            self.preview.setPixmap(pixmap)

    def clear_image(self):
        self.preview.setPixmap(QPixmap())


        