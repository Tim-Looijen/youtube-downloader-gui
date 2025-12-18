import tkinter as tk
from tkinter import filedialog, messagebox
import yt_dlp
import threading

import os
import sys
import requests
from datetime import datetime, timezone
import subprocess
import urllib.request
import tempfile

from pathlib import Path


APP_NAME = "YouTube Downloader"
MAIN_EXE = "youtube-downloader.exe"
OLD_EXE = "old-youtube-downloader.exe"


def get_runtime_paths():
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable)
        base_path = sys._MEIPASS  # folder where bundled files are extracted
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

def check_for_update(root, exe_path: Path):
    try:
        asset = get_latest_release()
        update_time = datetime.strptime(
            asset["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
        )
        current_time = datetime.fromtimestamp(
            exe_path.stat().st_ctime, tz=timezone.utc
        ).replace(tzinfo=None)

        if update_time <= current_time:
            return

        if not messagebox.askyesno("Update available", "Download and install update now?"):
            return

        import urllib.request
        import tempfile
        import subprocess

        app_dir = exe_path.parent
        new_exe = app_dir / MAIN_EXE
        temp_old = Path(tempfile.gettempdir()) / OLD_EXE

        urllib.request.urlretrieve(asset["browser_download_url"], new_exe)
        exe_path.replace(temp_old)

        subprocess.Popen([str(new_exe)], close_fds=True)
        root.quit()

    except Exception as e:
        messagebox.showerror("Update failed", str(e))


def download_complete_hook(d):
    if d['status'] == 'finished' and d['filename'].endswith('.mp4'):
        downloaded_file = d['filename']
        messagebox.showinfo("Success", "Download complete!")
        subprocess.Popen(fr'explorer /select,"{downloaded_file}"')

def start_download(root, url_entry, download_button, ffmpeg_path):
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return

    url = verify_link(url)
    save_dir = filedialog.askdirectory(
        title="Choose download folder",
        initialdir=get_download_folder(),
    )
    if not save_dir:
        return

    download_button.config(state="disabled", text="Downloading...")

    def worker():
        try:
            ydl_opts: yt_dlp._Params = {
                "outtmpl": f"{save_dir}/%(title)s.%(ext)s",
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                "merge_output_format": "mp4",
                "ffmpeg_location": ffmpeg_path,
                "progress_hooks": [download_complete_hook],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            messagebox.showerror("Download failed", str(e))
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

    tk.Label(root, text="Enter YouTube URL:").pack(pady=(20, 5))
    url_entry = tk.Entry(root, width=75)
    url_entry.pack(pady=5)

    download_button = tk.Button(
        root,
        text="Download",
        command=lambda: start_download(
            root, url_entry, download_button, ffmpeg_path
        ),
    )
    download_button.pack(pady=15)

    root.after(100, lambda: check_for_update(root, exe_path))
    root.mainloop()


if __name__ == "__main__":
    main()
