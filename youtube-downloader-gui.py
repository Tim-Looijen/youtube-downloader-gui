import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import yt_dlp
import threading
import hashlib
import os
import sys
import requests
import subprocess
import urllib.request
import tempfile


APP_NAME = "YouTube Downloader"
MAIN_EXE = "youtube-downloader.exe"
OLD_EXE = "old-youtube-downloader.exe"

FILE_FORMAT_MAP = {
    "Video (MP4)": "mp4",
    "Audio (MP3)": "mp3",
}

def get_runtime_paths():
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable)
        base_path = sys._MEIPASS  # folder where bundled files are extracted in windows
    else:
        exe_path = Path(__file__).resolve()
        base_path = exe_path.parent

    return exe_path, base_path


def get_download_folder() -> str:
    downloads = Path.home() / "Downloads"
    return str(downloads if downloads.exists() else Path.home())

def verify_link(url: str) -> str:
    return url.split("&", 1)[0]

def get_latest_release():
    url = "https://api.github.com/repos/Tim-Looijen/youtube-downloader-gui/releases/latest"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()["assets"][0]


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def update_needed(asset, exe_path: Path):
    sha256_local = sha256_of_file(exe_path)
    sha256_remote = asset["digest"].replace("sha256:", "")

    if sha256_remote and sha256_local != sha256_remote:
        return True


def check_for_update(root, exe_path: Path):
    try:
        asset = get_latest_release()
        if not update_needed(asset, exe_path):
            return

        if not messagebox.askyesno("Update beschikbaar", "Er is een update beschikbaar. Nu downloaden en installeren?"):
            return

        app_dir = exe_path.parent
        new_exe = app_dir / MAIN_EXE
        temp_old = Path(tempfile.gettempdir()) / OLD_EXE

        urllib.request.urlretrieve(asset["browser_download_url"], new_exe)
        exe_path.replace(temp_old)

        subprocess.Popen([str(new_exe)], close_fds=True)
        root.quit()

    except Exception as e:
        messagebox.showerror("Update failed", str(e))


def download_complete_hook(d, file_format):
    if d['status'] == 'finished' and d['filename'].endswith(f'.{file_format}'):
        downloaded_file = d.get("filename")
        messagebox.showinfo("Klaar", "Download voltooid!")
        subprocess.Popen(fr'explorer /select,"{downloaded_file}"')


def start_download(url_entry, download_button, ffmpeg_path, format_label):
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Fout", "Geef een geldige YouTube URL op.")
        return

    file_format = FILE_FORMAT_MAP.get(format_label)

    url = verify_link(url)
    save_dir = filedialog.askdirectory(
        title="Kies Download Folder",
        initialdir=get_download_folder(),
    )
    if not save_dir:
        return

    download_button.config(state="disabled", text="Bezig met downloaden...")

    def worker():
        try:
            if file_format == "mp3":
                ydl_opts: yt_dlp._Params = {
                    "outtmpl": f"{save_dir}/%(title)s.%(ext)s",
                    "format": "bestaudio/best",
                    "ffmpeg_location": ffmpeg_path,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                    "progress_hooks": [lambda d: download_complete_hook(d, file_format)],
                }
            else:
                ydl_opts: yt_dlp._Params = {
                    "outtmpl": f"{save_dir}/%(title)s.%(ext)s",
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                    "merge_output_format": "mp4",
                    "ffmpeg_location": ffmpeg_path,
                    "progress_hooks": [lambda d: download_complete_hook(d, file_format)],
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            messagebox.showerror("Downloaden mislukt", str(e))
        finally:
            download_button.config(state="normal", text="Download")

    threading.Thread(target=worker, daemon=True).start()


def main():
    exe_path, base_path = get_runtime_paths()
    ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("400x180")
    root.resizable(False, False)

    tk.Label(root, text="Voer hier de YouTube URL in:").pack(pady=(20, 5))
    url_entry = tk.Entry(root, width=75)
    url_entry.pack(pady=5)

    format_var = tk.StringVar(value= next(iter(FILE_FORMAT_MAP)))

    button_frame = tk.Frame(root)
    button_frame.pack(pady=15)

    download_button = tk.Button(
        button_frame,
        text="Download",
        command=lambda: start_download(
            url_entry, download_button, ffmpeg_path, format_var
        ),
    )

    download_button.pack(side="left")

    format_menu = tk.OptionMenu(button_frame, format_var, *FILE_FORMAT_MAP.keys())
    format_menu.config(width=12)
    format_menu.pack(side="left", padx=(10, 0))

    button_frame.pack(anchor="center")

    root.after(100, lambda: check_for_update(root, exe_path))
    root.mainloop()

if __name__ == "__main__":
    main()
