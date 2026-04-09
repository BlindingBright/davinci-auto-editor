import os
import config

class MusicFetcher:
    def fetch_for_style(self, style: str) -> str:
        print(f"[AI] Initializing yt-dlp to fetch royalty-free music for style: {style}...")
        
        query = config.YT_SEARCH_QUERIES.get(style, config.YT_SEARCH_QUERIES["vlog"])
        # Use TEMP_DIR from config instead of hardcoded C:/temp
        music_filename = f"downloaded_music_{style}"
        output_path = os.path.join(config.TEMP_DIR, music_filename)
        
        # Check for cached file with various extensions
        for ext in [".mp3", ".m4a", ".webm", ".wav"]:
            full_path = output_path + ext
            if os.path.exists(full_path):
                print(f"[AI] Using cached music for {style}: {full_path}")
                return full_path

        try:
            import yt_dlp
        except ImportError:
            print("[AI] Error: yt-dlp not installed.")
            return ""

        import subprocess
        has_ffmpeg = False
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            has_ffmpeg = True
        except:
            print("[AI] Warning: ffmpeg not found. Post-processing disabled.")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path + ".%(ext)s",
            'quiet': True,
            'no_warnings': True,
        }
        
        if has_ffmpeg:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        
        try:
            print(f"[AI] Downloading music for {style} (this may take a moment)...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                downloaded_file = ydl.prepare_filename(info)
                
                if has_ffmpeg:
                    # After post-processing, extension changes to .mp3
                    downloaded_file = downloaded_file.rsplit('.', 1)[0] + ".mp3"
            
            if os.path.exists(downloaded_file):
                # Ensure it has an extension for librosa/Resolve
                if "." not in os.path.basename(downloaded_file):
                    new_path = downloaded_file + ".m4a"
                    os.rename(downloaded_file, new_path)
                    print(f"[AI] Renamed extensionless music to {new_path}")
                    return new_path
                print(f"[AI] Music successfully downloaded to {downloaded_file}")
                return downloaded_file
            else:
                # Fallback: check for any file with that base name in TEMP_DIR
                for f in os.listdir(config.TEMP_DIR):
                    if f.startswith(music_filename):
                        found = os.path.join(config.TEMP_DIR, f)
                        if "." not in f:
                            new_found = found + ".m4a"
                            os.rename(found, new_found)
                            found = new_found
                        print(f"[AI] Music found via fallback search: {found}")
                        return found
                print(f"[AI] Warning: Music file not found at {downloaded_file}")
                return ""
        except Exception as e:
            print(f"[AI] WARNING: yt-dlp download failed: {e}")
            return ""
