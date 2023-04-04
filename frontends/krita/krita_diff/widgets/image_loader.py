from krita import QApplication, QFileDialog, QPixmap, QPushButton, QVBoxLayout, QHBoxLayout, Qt
from ..widgets import QLabel

class ImageLoaderLayout(QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super(ImageLoaderLayout, self).__init__(*args, **kwargs)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.import_button = QPushButton('Import image')
        self.paste_button = QPushButton('Paste image')
        self.clear_button = QPushButton('Clear')

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.paste_button)

        self.addLayout(button_layout)
        self.addWidget(self.clear_button)
        self.addWidget(self.preview)

        self.import_button.released.connect(self.load_image)
        self.paste_button.released.connect(self.paste_image)
        self.clear_button.released.connect(self.clear_image)

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self.import_button, 'Open File', '', 'Image Files (*.png *.jpg *.bmp)')
        if file_name:
            pixmap = QPixmap(file_name)

            if pixmap.width() > self.preview.width():
                pixmap = pixmap.scaledToWidth(self.preview.width(), Qt.SmoothTransformation)
                
            self.preview.setPixmap(pixmap)

    def paste_image(self):
        self.clear_image()
        pixmap = QPixmap(QApplication.clipboard().pixmap())

        if pixmap.width() > self.preview.width():
            pixmap = pixmap.scaledToWidth(self.preview.width(), Qt.SmoothTransformation)

        self.preview.setPixmap(pixmap)

    def clear_image(self):
        self.preview.setPixmap(QPixmap())


        