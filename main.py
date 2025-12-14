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

old_exe_name = "old-youtube-downloader.exe"
main_exe_name = "youtube-downloader.exe"

# determine if application is a script file or frozen exe
if getattr(sys, 'frozen', False):
    application_path = os.path.abspath(sys.executable)
    base_path = sys._MEIPASS  # folder where bundled files are extracted
else:
    application_path = os.path.abspath(__file__)
    base_path = os.path.dirname(__file__)

# Path to the bundled ffmpeg
ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")

def get_github_response():
    github_url = "https://api.github.com/repos/Tim-Looijen/youtube-downloader-gui/releases/latest"
    return requests.get(github_url).json()["assets"][0]

def check_for_update():
    github_release_asset = get_github_response()

    update_time = datetime.strptime(github_release_asset['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
    current_creation_time = datetime.fromtimestamp(os.path.getctime(application_path), tz=timezone.utc).replace(tzinfo=None)

    if (update_time > current_creation_time):
        if (messagebox.askyesno("Update", "New update available, would you like to update it now?")):
            application_dir = os.path.dirname(application_path)

            updated_old_name = os.path.join(application_dir, main_exe_name)
            os.rename(application_path, updated_old_name);

            new_exe_url = github_release_asset["browser_download_url"]
            urllib.request.urlretrieve(new_exe_url, main_exe_name)[0]

            temp_dir = tempfile.gettempdir()
            os.rename(updated_old_name, os.path.join(temp_dir, old_exe_name))

            subprocess.Popen([os.path.join(application_dir, main_exe_name)], close_fds=True)
            sys.exit()


def verify_link(link: str) -> str:
    good_link = link
    if (link.__contains__("&")):
        good_link = link.split("&")[0]
        return good_link
    return link


def get_download_folder() -> str:
    if os.name == "nt":  # Windows
        import ctypes.wintypes

        CSIDL_PERSONAL = 0x0005  # My Documents
        SHGFP_TYPE_CURRENT = 0

        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        # Use known folder Downloads path
        try:
            from ctypes import windll

            # Windows 10/11 Downloads folder
            from ctypes import wintypes

            _SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
            FOLDERID_Downloads = ctypes.c_char_p(
                b"\x11\x32\x02\xE5\x00\x00\x00\x00\xC0\x00\x00\x00\x00\x00\x00\x46"
            )
        except Exception:
            return str(Path.home() / "Downloads")
        return str(Path.home() / "Downloads")
    else:
        home = Path.home()
        downloads = home / "Downloads"
        return str(downloads if downloads.exists() else home)

def download_complete_hook(d):
    if d['status'] == 'finished' and d['filename'].endswith('.mp4'):
        downloaded_file = d['filename']
        messagebox.showinfo("Success", "Download complete!")
        subprocess.Popen(fr'explorer /select,"{downloaded_file}"')

def download_video():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return
    url = verify_link(url)

    # Ask user where to save
    save_path = filedialog.askdirectory(initialdir=get_download_folder(), title="Choose download folder")
    if not save_path:
        return

    # Disable the button while downloading
    download_button.config(state="disabled", text="Downloading...")

    def run_download():
        try:
            ydl_opts: yt_dlp._Params  = {
                'outtmpl': f'{save_path}/%(title)s.%(ext)s',
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                "ffmpeg_location": ffmpeg_path,
                'merge_output_format': 'mp4',
            }

            ydl_opts['progress_hooks'] = [download_complete_hook]
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to download: {e}")
        finally:
            download_button.config(state="normal", text="Download")

    # Run download in a thread so the UI doesn't freeze
    threading.Thread(target=run_download, daemon=True).start()

# --- UI setup ---
root = tk.Tk()
root.title("YouTube Downloader")
root.geometry("400x180")
root.resizable(False, False)

tk.Label(root, text="Enter YouTube URL:").pack(pady=(20, 5))

url_entry = tk.Entry(root, width=75)
url_entry.pack(pady=5)

download_button = tk.Button(root, text="Download", command=download_video)
download_button.pack(pady=15)

root.after(1, check_for_update)

root.mainloop()

