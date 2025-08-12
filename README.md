# AVIF Converter GUI

Simple GUI to convert common image files to AVIF. Drag and drop supported.

## Run locally
1. python -m venv venv
2. venv\Scripts\activate
3. pip install -r requirements.txt
4. python converter.py

## Build EXE
1. pip install pyinstaller
2. pyinstaller --onefile --windowed --name convert2avif --icon convert2avif.ico --hidden-import pillow_avif --collect-data pillow_avif --collect-all tkinterdnd2 --add-data "convert2avif.ico;." converter.py
3. EXE in dist\converter.exe
