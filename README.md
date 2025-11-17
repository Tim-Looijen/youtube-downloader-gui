pyinstaller command (run in windows, activate .venv2 first):
pyinstaller --onefile --noconsole --add-binary="C:\Users\tim\youtube-downloader-gui\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe;." --add-binary="C:\Users\tim\youtube-downloader-gui\deno-x86_64-pc-windows-msvc\deno.exe;." C:\Users\tim\youtube-downloader-gui\main.py
