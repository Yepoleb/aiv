#Advance Image Viewer

GUI for viewing compressed and uncompressed Images in GBA-ROMs.
Supports 4, 16 and 256 color mode.

##Dependencies
* [TileCodecs]
* [PyQt5]
* [Pillow]

##Usage
1. Run `python3 aiv.py`
2. Select a ROM in File -> Open ROM
3. Enter an offset or use the Next/Previous Image buttons to scroll through 
   all compressed Images.

##Credits
cosarara97 - lz77.py and some Qt code.

[TileCodecs]:https://github.com/Yepoleb/TileCodecs
[PyQt5]:https://www.riverbankcomputing.com/software/pyqt/download5
[Pillow]:http://python-pillow.github.io/
