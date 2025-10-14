from collections.abc import Collection
import yt_dlp

def main():
    a = ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    yt_download = yt_dlp.YoutubeDL()
    yt_download.download(a);

if __name__ == "__main__":
    main()
