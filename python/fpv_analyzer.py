import os
import numpy as np
import config

class FPVAnalyzer:
    def __init__(self):
        pass

    def analyze_directory(self, folder_path: str) -> list:
        """Analyzes a directory of FPV footage to identify 'flying' segments."""
        if not folder_path or not os.path.exists(folder_path):
            return []
        
        video_exts = (".mp4", ".mov", ".mkv", ".m4v", ".avi", ".mts")
        files = [f for f in sorted(os.listdir(folder_path)) if f.lower().endswith(video_exts)]
        print(f"[AI] Analyzing {len(files)} FPV files...")
        
        results = []
        for file in files:
            file_path = os.path.join(folder_path, file)
            print(f"[AI] Detecting flight vs ground states for {file}...")
            result = self._analyze_with_opencv(file_path)
            results.append(result)
            print(f"  Found {len(result['useful_segments'])} flight segment(s)")

        return results


    def _analyze_with_opencv(self, file):
        """Fallback: N evenly-spaced seeks with OpenCV."""
        import cv2
        N_SAMPLES = 10
        target_w, target_h = 160, 90

        cap = cv2.VideoCapture(file)
        if not cap.isOpened():
            return {"file": file, "useful_segments": []}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        print(f"  Duration: {duration:.0f}s | Frames: {total_frames} (opencv mode)")

        step = max(total_frames // N_SAMPLES, 1)
        ret, prev = cap.read()
        prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY) if ret else None
        prev_gray = cv2.resize(prev_gray, (target_w, target_h)) if prev_gray is not None else None

        motion_scores = []
        for i in range(1, N_SAMPLES + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            ret, frame = cap.read()
            if not ret or prev_gray is None:
                break
            gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (target_w, target_h))
            score = float(np.mean(cv2.absdiff(prev_gray, gray)))
            motion_scores.append((i * step / fps, score))
            prev_gray = gray
        cap.release()
        print(f"  Sampled {len(motion_scores)} points")
        return self._segments_from_scores(motion_scores, file)

    def _segments_from_scores(self, motion_scores: list, file: str) -> dict:
        """Convert (timestamp, score) list into flying segment ranges based on adaptive threshold."""
        if not motion_scores:
            return {"file": file, "useful_segments": []}
            
        all_scores = [s for _, s in motion_scores]
        # Use configurable multiplier and min threshold from config.py
        threshold = max(np.median(all_scores) * config.FPV_MOTION_THRESHOLD_MULT, config.FPV_MIN_THRESHOLD)

        flying_segments = []
        start_flying = None
        current_segment_scores = []
        
        for timestamp, score in motion_scores:
            if score > threshold and start_flying is None:
                start_flying = timestamp
                current_segment_scores = [score]
            elif score <= threshold and start_flying is not None:
                if timestamp - start_flying >= config.FPV_MIN_SEGMENT_DUR:
                    max_motion = max(current_segment_scores)
                    flying_segments.append((round(start_flying, 1), round(timestamp, 1), round(max_motion, 1)))
                start_flying = None
                current_segment_scores = []
            elif start_flying is not None:
                current_segment_scores.append(score)
        
        if start_flying is not None and (motion_scores[-1][0] - start_flying) >= config.FPV_MIN_SEGMENT_DUR:
            max_motion = max(current_segment_scores) if current_segment_scores else 0
            flying_segments.append((round(start_flying, 1), round(motion_scores[-1][0], 1), round(max_motion, 1)))

        return {"file": file, "useful_segments": flying_segments}
