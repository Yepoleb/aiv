#!/usr/bin/env python3

import sys
import bisect
from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import Image, ImageQt
from tilecodecs import LinearCodec

from aiv_ui import Ui_MainWindow
import decode

class Window(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.scene = QtWidgets.QGraphicsScene()
        self.ui.graphicsView.setScene(self.scene)
        
        self.ui.actionQuit.triggered.connect(self.onQuit)
        self.ui.actionOpen.triggered.connect(self.load_rom)
        self.ui.actionSaveImage.triggered.connect(self.save_image)
        
        self.ui.previmgButton.clicked.connect(self.prev_image)
        self.ui.nextimgButton.clicked.connect(self.next_image)
        self.ui.prevpalButton.clicked.connect(self.prev_palette)
        self.ui.nextpalButton.clicked.connect(self.next_palette)
        
        self.ui.widthSpin.valueChanged.connect(self.update_width)
        self.ui.zoomSpin.valueChanged.connect(self.update_zoom)
        self.ui.colorsSelect.currentIndexChanged.connect(self.update_codec)
        self.ui.tilemapCheck.toggled.connect(self.update_tilemap_enabled)
        
        self.ui.imageInput.editingFinished.connect(self.update_image)
        self.ui.paletteInput.editingFinished.connect(self.update_palette)
        self.ui.tilemapInput.editingFinished.connect(self.update_tilemap)
        
        self.rom = None
        self.pointers = []
        self.codec = None
        
        self.img_pointer = 0
        self.palette_pointer = 0
        self.tilemap_pointer = 0
        self.scale = 2
        self.width = 16
        self.tilemap_enabled = False
        self.display_img = None

        self.update_codec()
    
    def load_rom(self):
        filename, filter_ = QtWidgets.QFileDialog.getOpenFileName(self, "Open ROM file",
            QtCore.QDir.homePath(), "GBA ROM (*.gba);;All files (*)")
        print(filename)
        if not filename:
            return
        
        with open(filename, "rb") as rom_file:
            self.rom = rom_file.read()
        all_pointers = decode.find_pointers(self.rom)
        self.pointers = []
        for pointer in all_pointers:
            if decode.check_valid(self.rom, pointer, strict=False):
                self.pointers.append(pointer)
        self.next_image()
        self.next_palette()
        self.show_status("ROM loaded")

    def set_image(self, pointer):
        self.img_pointer = pointer
        self.ui.imageInput.setText("0x{:X}".format(pointer))
        self.decode_image()

    def set_palette(self, pointer):
        self.palette_pointer = pointer
        self.ui.paletteInput.setText("0x{:X}".format(pointer))
        self.decode_image()

    def set_tilemap(self, pointer):
        self.tilemap_pointer = pointer
        self.ui.tilemapInput.setText("0x{:X}".format(pointer))
        self.decode_image()

    def decode_image(self):
        if self.rom is None:
            self.show_status("No ROM loaded")
            return

        print("Decoding", hex(self.img_pointer))
        if self.tilemap_enabled:
            img = decode.decode_tilemap_at(self.rom, self.codec, self.img_pointer,
                self.palette_pointer, self.tilemap_pointer, self.width)
        else:
            img_offset = decode.get_rom_addr(self.img_pointer)
            next_offset = self.next_pointer(self.img_pointer)
            if next_offset is not None:
                img_len = next_offset - img_offset
            else:
                img_len = len(self.rom) - img_offset
            if img_len > 20480:
                img_len = 20480
            
            img = decode.decode_image_at(self.rom, self.codec, self.img_pointer,
                self.palette_pointer, img_len, self.width)
        
        if type(img) == str: # Error
            error = img
            if error == "PALETTE_TOO_SMALL":
                self.show_status("The compressed data at {} is too small for "
                    "a palette".format(hex(self.palette_pointer)))
            elif error == "PALETTE_DECODE_FAILED":
                self.show_status("Failed to decode palette at {}".format(
                    hex(self.palette_pointer)))
            elif error == "IMAGE_DECODE_FAILED":
                self.show_status("Failed to decode image at {}".format(
                    hex(self.img_pointer)))
            elif error == "TILEMAP_DECODE_FAILED":
                self.show_status("Failed to decode tilemap at {}".format(
                    hex(self.tilemap_pointer)))
            else:
                self.show_status("Unknow error {} occured".format(error))
            img = Image.open("error.png")
        elif not all(x > 0 for x in img.size):
            self.show_status("Image has a size of 0")
            img = Image.open("error.png")
        else: # Success!
            orig_size = img.size
            new_size = (img.size[0] * self.scale, img.size[1] * self.scale)
            img = img.resize(new_size)
            self.clear_status()

        self.display_img = img
        img_qt = ImageQt.ImageQt(self.display_img)
        pixmap = QtGui.QPixmap.fromImage(img_qt)
        pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)
        self.scene.clear()
        self.scene.addItem(pixmap_item)
        self.scene.update()
        self.scene.setSceneRect(0,0, img.size[0], img.size[1])
    
    def save_image(self):
        filename, filter_ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Image",
            QtCore.QDir.homePath(), "PNG Image (*.png);;All files (*)")
        if not filename:
            return
        
        if not filename.lower().endswith(".png"):
            filename += ".png"
        
        if not self.display_img:
            self.show_status("No Image loaded")
            return
        
        self.display_img.save(filename)
        self.show_status("Saved Image!")
    
    def next_pointer(self, pointer):
        new_index = bisect.bisect_right(self.pointers, pointer)
        if new_index < len(self.pointers):
            return self.pointers[new_index]
        else:
            return None

    def prev_pointer(self, pointer):
        new_index = bisect.bisect_left(self.pointers, pointer) - 1
        if new_index >= 0:
            return self.pointers[new_index]
        else:
            return None

    def next_image(self):
        new_pointer = self.next_pointer(self.img_pointer)
        if new_pointer is not None:
            self.set_image(new_pointer)
    
    def prev_image(self):
        new_pointer = self.prev_pointer(self.img_pointer)
        if new_pointer is not None:
            self.set_image(new_pointer)

    def next_palette(self):
        new_pointer = self.next_pointer(self.palette_pointer)
        if new_pointer is not None:
            self.set_palette(new_pointer)
    
    def prev_palette(self):
        new_pointer = self.prev_pointer(self.palette_pointer)
        if new_pointer is not None:
            self.set_palette(new_pointer)
    
    def update_width(self):
        self.width = self.ui.widthSpin.value()
        self.decode_image()
    
    def update_zoom(self):
        self.scale = self.ui.zoomSpin.value()
        self.decode_image()
    
    def update_codec(self):
        codec_text = self.ui.colorsSelect.currentText()
        if "2bpp" in codec_text:
            self.codec = LinearCodec(2, LinearCodec.REVERSE_ORDER)
        elif "8bpp" in codec_text:
            self.codec = LinearCodec(8, LinearCodec.REVERSE_ORDER)
        else: # 4bpp
            self.codec = LinearCodec(4, LinearCodec.REVERSE_ORDER)
        self.decode_image()

    def parse_int(self, int_str):
        try:
            num = int(int_str, 0)
            return num
        except:
            self.ui.statusbar.showMessage("Could not convert {} to a number"
                .format(int_str))
            return None

    def update_image(self):
        pointer_str = self.ui.imageInput.text()
        pointer = self.parse_int(pointer_str)
        if pointer is None:
            return
        self.set_image(pointer)

    def update_palette(self):
        pointer_str = self.ui.paletteInput.text()
        pointer = self.parse_int(pointer_str)
        if pointer is None:
            return
        self.set_palette(pointer)

    def update_tilemap(self):
        pointer_str = self.ui.tilemapInput.text()
        pointer = self.parse_int(pointer_str)
        if pointer is None:
            return
        self.set_tilemap(pointer)
    
    def update_tilemap_enabled(self):
        self.tilemap_enabled = self.ui.tilemapCheck.isChecked()
        if self.tilemap_enabled:
            self.ui.tilemapLabel.setEnabled(True)
            self.ui.tilemapInput.setEnabled(True)
        else:
            self.ui.tilemapLabel.setEnabled(False)
            self.ui.tilemapInput.setEnabled(False)
        self.decode_image()
    
    def show_status(self, text):
        self.ui.statusbar.showMessage(text)
        print(text)
    
    def clear_status(self):
        self.ui.statusbar.clearMessage()

    def onQuit(self):
        win.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    try:
        win = Window()
    except:
        app.deleteLater()
        raise
    win.show()
    r = app.exec_()
    win.close()
    app.deleteLater()
    sys.exit(r)
