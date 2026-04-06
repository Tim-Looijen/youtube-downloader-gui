import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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

QUALITY_MAP = {
    "Aanbevolen": "recommended",
    "Beste": "best",
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


def start_download(url_entry, download_button, format_menu, quality_label, quality_menu, main_frame, ffmpeg_path, format_var, quality_var):
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Fout", "Geef een geldige YouTube URL op.")
        return

    file_format = FILE_FORMAT_MAP.get(format_var.get())
    quality = QUALITY_MAP.get(quality_var.get())

    url = verify_link(url)
    save_dir = filedialog.askdirectory(
        title="Kies Download Folder",
        initialdir=get_download_folder(),
    )

    if not save_dir:
        return


    download_button.pack_forget()
    format_menu.pack_forget()
    quality_label.pack_forget()
    quality_menu.pack_forget()

    progress_bar = ttk.Progressbar(main_frame, length=300)
    progress_bar.pack(pady=10)
    progress_bar["value"] = 0

    def worker():
        try:
            def progress_hook(d):
                if d["status"] == "downloading":
                    total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded_bytes = d.get("downloaded_bytes", 0)

                    if total_bytes:
                        raw = downloaded_bytes / total_bytes
                        # Ease-out curve that approaches 90% but never reaches it
                        progress = 90 * (1 - (1 - raw) ** 3)
                        progress_bar["value"] = progress

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
                    "progress_hooks": [progress_hook],
                }
            else:
                if quality == "recommended":
                    # Limit to max 1920x1080, best audio
                    format_string = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]"
                else:
                    # Default best quality
                    format_string = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"

                ydl_opts: yt_dlp._Params = {
                    "outtmpl": f"{save_dir}/%(title)s.%(ext)s",
                    "format": format_string,
                    "merge_output_format": "mp4",
                    "ffmpeg_location": ffmpeg_path,
                    "progress_hooks": [progress_hook],
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                output_file = Path(ydl.prepare_filename(info))
                if file_format == "mp3":
                    output_file = output_file.with_suffix(".mp3")

                ydl.download([url])

            progress_bar["value"] = 100
            messagebox.showinfo("Klaar", f"Download voltooid: {output_file.name}")
            subprocess.Popen(fr'explorer /select,"{output_file}"')

        except Exception as e:
            messagebox.showerror("Downloaden mislukt", str(e))
        finally:
            # Remove progress bar and restore button + format menu
            progress_bar.pack_forget()
            download_button.pack(side="left")
            format_menu.pack(side="left", padx=(10, 0))
            quality_label.pack(side="left", padx=(10, 0))
            quality_menu.pack(side="left", padx=(10, 0))

    threading.Thread(target=worker, daemon=True).start()


def main():
    exe_path, base_path = get_runtime_paths()
    ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("450x200")
    root.resizable(False, False)

    tk.Label(root, text="Voer hier de YouTube URL in:").pack(pady=(20, 5))
    url_entry = tk.Entry(root, width=75)
    url_entry.pack(pady=5)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=15)
    button_frame.pack(anchor="center")

    download_button = tk.Button(button_frame, text="Download")
    download_button.pack(side="left")

    format_var = tk.StringVar(value= next(iter(FILE_FORMAT_MAP)))
    format_menu = tk.OptionMenu(button_frame, format_var, *FILE_FORMAT_MAP.keys())
    format_menu.config(width=12)
    format_menu.pack(side="left", padx=(10, 0))

    quality_var = tk.StringVar(value="Aanbevolen")

    quality_label = tk.Label(button_frame, text="Kwaliteit (video):")
    quality_label.pack(side="left", padx=(15, 5))

    quality_menu = tk.OptionMenu(button_frame, quality_var, *QUALITY_MAP.keys())
    quality_menu.config(width=12)
    quality_menu.pack(side="left")

    download_button.config(command=lambda: start_download(url_entry, download_button, format_menu, quality_label, quality_menu, button_frame, ffmpeg_path, format_var, quality_var))

    root.after(100, lambda: check_for_update(root, exe_path))
    root.mainloop()


if __name__ == "__main__":
    main()
