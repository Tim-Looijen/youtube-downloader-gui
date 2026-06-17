import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from dataclasses import dataclass
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


# --------------------------------------------------------------------------- #
# Runtime paths
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RuntimePaths:
    """Locations that differ between a source run and a PyInstaller build."""
    exe_path: Path
    base_path: str

    @property
    def ffmpeg(self) -> str:
        return os.path.join(self.base_path, "ffmpeg.exe")

    @property
    def deno(self) -> str:
        return os.path.join(self.base_path, "deno.exe")


def get_runtime_paths() -> RuntimePaths:
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable)
        base_path = sys._MEIPASS  # folder where bundled files are extracted on Windows
    else:
        exe_path = Path(__file__).resolve()
        base_path = str(exe_path.parent)

    return RuntimePaths(exe_path, base_path)


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def get_download_folder() -> str:
    downloads = Path.home() / "Downloads"
    return str(downloads if downloads.exists() else Path.home())


def verify_link(url: str) -> str:
    return url.split("&", 1)[0]


# --------------------------------------------------------------------------- #
# Self-update
# --------------------------------------------------------------------------- #
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


def update_needed(asset, exe_path: Path) -> bool:
    sha256_local = sha256_of_file(exe_path)
    sha256_remote = asset["digest"].replace("sha256:", "")
    return bool(sha256_remote and sha256_local != sha256_remote)


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


# --------------------------------------------------------------------------- #
# Diagnostics (used to debug frozen-build download failures)
# --------------------------------------------------------------------------- #
class _CaptureLogger:
    """Minimal yt-dlp logger that captures every message for diagnostics."""
    def __init__(self):
        self.lines = []
    def debug(self, msg):
        self.lines.append(str(msg))
    def info(self, msg):
        self.lines.append(str(msg))
    def warning(self, msg):
        self.lines.append("WARNING: " + str(msg))
    def error(self, msg):
        self.lines.append("ERROR: " + str(msg))


def _probe(cmd, stdin=None):
    """Run a command two ways: plain subprocess, and yt-dlp's PyInstaller-aware
    Popen. Differences between the two pinpoint a frozen-build subprocess issue."""
    out = []
    try:
        kw = {"capture_output": True, "text": True, "timeout": 60}
        if stdin is None:
            kw["stdin"] = subprocess.DEVNULL  # windowed build has no valid stdin handle
        else:
            kw["input"] = stdin
        p = subprocess.run(cmd, **kw)
        out.append(f"[plain]      rc={p.returncode} stdout={p.stdout.strip()!r} stderr={p.stderr.strip()!r}")
    except Exception as ex:
        out.append(f"[plain]      EXCEPTION: {ex!r}")
    try:
        from yt_dlp.utils import Popen
        proc = Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        so, se = proc.communicate(stdin)
        out.append(f"[ytdlp Popen] rc={proc.returncode} stdout={so.strip()!r} stderr={se.strip()!r}")
    except Exception as ex:
        out.append(f"[ytdlp Popen] EXCEPTION: {ex!r}")
    return "\n".join(out)


def write_debug_report(paths: RuntimePaths, url, logger, error) -> Path:
    """Dump everything we need to diagnose a frozen-build download failure."""
    lines = []
    a = lines.append
    a("=== YouTube Downloader debug report ===")
    a(f"url   : {url}")
    a(f"error : {error!r}")
    a("")
    a("--- runtime ---")
    a(f"sys.frozen     = {getattr(sys, 'frozen', False)}")
    a(f"sys.executable = {sys.executable}")
    a(f"sys._MEIPASS   = {getattr(sys, '_MEIPASS', None)}")
    try:
        a(f"yt_dlp version = {yt_dlp.version.__version__}")
    except Exception as ex:
        a(f"yt_dlp version = ERR {ex!r}")
    a("")
    a("--- bundled binaries ---")
    for label, p in (("ffmpeg", paths.ffmpeg), ("deno", paths.deno)):
        try:
            exists = os.path.exists(p)
            size = os.path.getsize(p) if exists else "NA"
            a(f"{label:7}: {p}  exists={exists} size={size}")
        except Exception as ex:
            a(f"{label:7}: {p}  ERR {ex!r}")
    a("")
    a("--- relevant env ---")
    for k in ("DENO_DIR", "LOCALAPPDATA", "APPDATA", "TEMP", "TMP", "USERPROFILE", "PYINSTALLER_RESET_ENVIRONMENT"):
        a(f"{k} = {os.environ.get(k)}")
    a("")
    a("--- deno --version ---")
    a(_probe([paths.deno, "--version"]))
    a("")
    a("--- deno trivial run (console.log('deno-ok')) ---")
    a(_probe([paths.deno, "run", "--no-prompt", "-"], stdin="console.log('deno-ok')"))
    a("")
    a("--- yt-dlp verbose log ---")
    a("\n".join(getattr(logger, "lines", [])) or "(no log captured)")

    report = "\n".join(lines)
    log_path = Path.home() / "youtube-downloader-debug.log"
    try:
        log_path.write_text(report, encoding="utf-8")
    except Exception:
        log_path = Path(tempfile.gettempdir()) / "youtube-downloader-debug.log"
        log_path.write_text(report, encoding="utf-8")
    return log_path


# --------------------------------------------------------------------------- #
# Download core (no UI)
# --------------------------------------------------------------------------- #
def build_ydl_opts(save_dir, file_format, quality, paths: RuntimePaths, progress_hook, logger) -> dict:
    """Build the yt-dlp options dict for the requested format and quality."""
    opts: dict = {
        "outtmpl": f"{save_dir}/%(title)s.%(ext)s",
        "ffmpeg_location": paths.ffmpeg,
        "progress_hooks": [progress_hook],
    }

    if file_format == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["merge_output_format"] = "mp4"
        if quality == "recommended":
            # Cap at 1080p, with the best matching audio.
            opts["format"] = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]"
        else:
            # Best available quality.
            opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"

    # Let deno fetch (and cache) the npm packages its YouTube JS-challenge solver
    # needs on first run. Without this, yt-dlp runs deno with --cached-only/--no-remote.
    opts["remote_components"] = ["ejs:npm"]

    # Point yt-dlp at the bundled Deno so it can solve YouTube's JS challenges
    # (nsig/signature). Only when the bundled binary exists (the frozen build);
    # from source we let yt-dlp auto-detect deno/node on PATH.
    if os.path.exists(paths.deno):
        opts["js_runtimes"] = {"deno": {"path": paths.deno}}

    # DIAGNOSTIC: capture yt-dlp's full verbose output so a failure on a fresh
    # machine can be inspected (see write_debug_report).
    opts["verbose"] = True
    opts["logger"] = logger
    return opts


def run_download(url, save_dir, file_format, quality, paths: RuntimePaths, progress_hook, logger) -> Path:
    """Download `url` into `save_dir` and return the resulting file path."""
    opts = build_ydl_opts(save_dir, file_format, quality, paths, progress_hook, logger)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        output_file = Path(ydl.prepare_filename(info))
        if file_format == "mp3":
            output_file = output_file.with_suffix(".mp3")
        ydl.download([url])
    return output_file


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
class App:
    def __init__(self, root: tk.Tk, paths: RuntimePaths):
        self.root = root
        self.paths = paths
        self._build_ui()
        root.after(100, lambda: check_for_update(root, self.paths.exe_path))

    # ---- construction --------------------------------------------------- #
    def _build_ui(self):
        self.root.title(APP_NAME)
        self.root.geometry("450x180")
        self.root.resizable(False, False)

        tk.Label(self.root, text="Voer hier de YouTube URL in:").pack(pady=(20, 5))
        self.url_entry = tk.Entry(self.root, width=75)
        self.url_entry.pack(pady=5)

        self.controls = tk.Frame(self.root)
        self.controls.pack(pady=15)

        self.download_button = tk.Button(self.controls, text="Download", command=self.on_download)

        self.format_var = tk.StringVar(value=next(iter(FILE_FORMAT_MAP)))
        self.format_menu = tk.OptionMenu(self.controls, self.format_var, *FILE_FORMAT_MAP.keys())
        self.format_menu.config(width=12)

        self.quality_var = tk.StringVar(value="Aanbevolen")
        self.quality_label = tk.Label(self.controls, text="Kwaliteit (video):")
        self.quality_menu = tk.OptionMenu(self.controls, self.quality_var, *QUALITY_MAP.keys())
        self.quality_menu.config(width=12)

        self.progress_bar = ttk.Progressbar(self.controls, length=400)

        self._show_controls()

    # ---- layout --------------------------------------------------------- #
    def _show_controls(self):
        self.download_button.pack(side="left")
        self.format_menu.pack(side="left", padx=(10, 0))
        self.quality_label.pack(side="left", padx=(15, 5))
        self.quality_menu.pack(side="left")

    def _hide_controls(self):
        for widget in (self.download_button, self.format_menu, self.quality_label, self.quality_menu):
            widget.pack_forget()

    def _show_progress(self):
        self.progress_bar["value"] = 0
        self.progress_bar.pack(pady=10)

    def _hide_progress(self):
        self.progress_bar.pack_forget()

    # ---- download flow -------------------------------------------------- #
    def on_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Fout", "Geef een geldige YouTube URL op.")
            return

        url = verify_link(url)
        save_dir = filedialog.askdirectory(title="Kies Download Folder", initialdir=get_download_folder())
        if not save_dir:
            return

        file_format = FILE_FORMAT_MAP.get(self.format_var.get())
        quality = QUALITY_MAP.get(self.quality_var.get())

        self._hide_controls()
        self._show_progress()
        threading.Thread(
            target=self._worker,
            args=(url, save_dir, file_format, quality),
            daemon=True,
        ).start()

    def _worker(self, url, save_dir, file_format, quality):
        logger = _CaptureLogger()
        try:
            output_file = run_download(url, save_dir, file_format, quality, self.paths, self._on_progress, logger)
            self.progress_bar["value"] = 100
            messagebox.showinfo("Klaar", f"Download voltooid: {output_file.name}")
            subprocess.Popen(fr'explorer /select,"{output_file}"')
        except Exception as e:
            self._report_failure(url, logger, e)
        finally:
            self._hide_progress()
            self._show_controls()

    def _on_progress(self, d):
        if d["status"] != "downloading":
            return
        total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
        if not total_bytes:
            return
        raw = d.get("downloaded_bytes", 0) / total_bytes
        # Ease-out curve that approaches 90% but never quite reaches it.
        self.progress_bar["value"] = 90 * (1 - (1 - raw) ** 3)

    def _report_failure(self, url, logger, error):
        try:
            log_path = write_debug_report(self.paths, url, logger, error)
            detail = f"\n\nDebug-log opgeslagen:\n{log_path}"
        except Exception as ex:
            detail = f"\n\n(debug report failed: {ex!r})"
        messagebox.showerror("Downloaden mislukt", f"{error}{detail}")


def main():
    paths = get_runtime_paths()
    root = tk.Tk()
    App(root, paths)
    root.mainloop()


if __name__ == "__main__":
    main()
