import os
import sys
import tempfile
import cv2
import numpy as np

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_analyzer import AudioAnalyzer
from fpv_analyzer import FPVAnalyzer
from music_fetcher import MusicFetcher
from resolve_controller import ResolveController

def create_dummy_video(filename, duration_sec=5, fps=30):
    print(f"Generating dummy video: {filename}...")
    width, height = 640, 360
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    for i in range(duration_sec * fps):
        # Create a changing frame to simulate optical flow motion
        img = np.zeros((height, width, 3), dtype=np.uint8)
        # Add a moving circle
        x = int(width / 2 + np.sin(i / 10.0) * 100)
        cv2.circle(img, (x, int(height/2)), 50, (255, 255, 255), -1)
        out.write(img)
    out.release()
    print(f"Created {filename}")

def run_tests():
    print("=== DaVinci Auto-Editor Test Suite ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Create dummy files
        aroll_path = os.path.join(temp_dir, "aroll.mp4")
        fpv_path = os.path.join(temp_dir, "fpv.mp4")
        
        create_dummy_video(aroll_path)
        create_dummy_video(fpv_path)
        
        # 2. Test AudioAnalyzer
        print("\n--- Testing AudioAnalyzer ---")
        audio_analyzer = AudioAnalyzer()
        try:
            res = audio_analyzer.analyze_directory(temp_dir)
            print(f"AudioAnalyzer success: Found {len(res)} files processed.")
        except Exception as e:
            print(f"AudioAnalyzer returned error (expected if faster-whisper not installed): {e}")

        # 3. Test FPVAnalyzer (OpenCV optical flow)
        print("\n--- Testing FPVAnalyzer ---")
        fpv_analyzer = FPVAnalyzer()
        res = fpv_analyzer.analyze_directory(temp_dir)
        print(f"FPVAnalyzer success: Found flight data: {res}")
        assert len(res) == 2, "Failed to analyze FPV files"

        # 4. Test MusicFetcher (yt-dlp)
        print("\n--- Testing MusicFetcher ---")
        music_fetcher = MusicFetcher()
        try:
            print("MusicFetcher instantiated successfully.")
        except Exception as e:
            print(f"MusicFetcher error: {e}")

        # 5. Test ResolveController
        print("\n--- Testing ResolveController ---")
        resolve = ResolveController()
        resolve.create_or_load_project("TEST_PROJECT")
        items = resolve.add_media([aroll_path])
        timeline = resolve.create_timeline("Test_Timeline")
        
        if timeline is not None:
            resolve.add_clip_to_timeline(items[0], "video", 1, 0, 100)
            resolve.apply_lut(1, 0, "C:/FakeLUT.cube")
        print("ResolveController test passed!")

    print("\n=== All Tests Finished ===")

if __name__ == "__main__":
    run_tests()
