import os
import cv2
import numpy as np
import config
from typing import List, Dict, Tuple

class MotionAnalyzer:
    def __init__(self):
        pass

    def analyze_clip(self, file_path: str, max_duration: int = 60) -> Dict:
        """Analyzes a clip for visual motion intensity and finds stable/busy segments."""
        if not file_path or not os.path.exists(file_path):
            return {"file": file_path, "useful_segments": []}
            
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return {"file": file_path, "useful_segments": []}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = min(total_frames / fps, max_duration)
        
        # Sampling settings
        sample_step = max(int(fps * 2), 1) # Sample every 2 seconds
        target_w, target_h = 160, 90
        
        motion_scores = []
        ret, prev = cap.read()
        if not ret:
            cap.release()
            return {"file": file_path, "useful_segments": []}
            
        prev_gray = cv2.resize(cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY), (target_w, target_h))
        
        for f_idx in range(sample_step, int(duration * fps), sample_step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret: break
            
            gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (target_w, target_h))
            score = float(np.mean(cv2.absdiff(prev_gray, gray)))
            motion_scores.append((f_idx / fps, score))
            prev_gray = gray
            
        cap.release()
        
        # Segment and score
        if not motion_scores:
            return {"file": file_path, "useful_segments": [(0.0, duration, 0.5)]}
            
        # Use median as a base for intensity
        all_vals = [s for _, s in motion_scores]
        threshold = np.median(all_vals) * 0.8
        
        segments = []
        for i in range(len(motion_scores) - 2):
            s_time, s_score = motion_scores[i]
            e_time, e_score = motion_scores[i+2]
            avg_score = (s_score + motion_scores[i+1][1] + e_score) / 3.0
            
            if avg_score > threshold:
                segments.append((round(s_time, 1), round(e_time, 1), round(avg_score, 1)))
                
        # Sort internal segments by score
        segments.sort(key=lambda x: x[2], reverse=True)
        return {"file": file_path, "useful_segments": segments[:5]} # Return top 5 dynamic segments
