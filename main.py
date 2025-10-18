import tkinter as tk
from tkinter import filedialog, messagebox
import yt_dlp
import threading

import os
from pathlib import Path
#    yt_dlp.main(["--recode-video", "mp4", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"])


def get_download_folder() -> str:
    """Return the default Downloads folder for Windows, Linux, or fallback to home."""
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
        # Linux / macOS
        home = Path.home()
        downloads = home / "Downloads"
        return str(downloads if downloads.exists() else home)

def download_video():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return

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
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            messagebox.showinfo("Success", "Download complete!")
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

root.mainloop()

