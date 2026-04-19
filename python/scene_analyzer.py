"""
Scene Analyzer — Intelligent Clip Intelligence Engine

Performs deep analysis on source footage to make smarter editing decisions:
  - Face detection (talking-head vs action classification)
  - Color histogram clustering (visual cohesion between adjacent cuts)
  - Duplicate detection (prevent reusing the same B-Roll segment)
  - Scene complexity scoring (busy vs calm shots)
"""
import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
import hashlib

import config


class SceneAnalyzer:
    """Deep visual intelligence for smarter clip selection and sequencing."""

    def __init__(self):
        # Load face detection cascade
        self.face_cascade = None
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if os.path.exists(cascade_path):
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            print("[SceneAnalyzer] Face detection model loaded")
        else:
            print("[SceneAnalyzer] Warning: Face cascade not found — face detection disabled")
        
        # Frame hash set for duplicate detection
        self._seen_hashes: Set[str] = set()

    # ------------------------------------------------------------------
    #  Face Detection — Is this a talking head or action footage?
    # ------------------------------------------------------------------
    def detect_faces_in_clip(self, file_path: str, sample_count: int = 5) -> Dict:
        """
        Samples N frames from a clip and detects faces in each.
        
        Returns:
            {
                "file": str,
                "has_face": bool,
                "face_ratio": float,       # Fraction of sampled frames with faces
                "avg_face_size": float,     # Average face size relative to frame (0-1)
                "is_talking_head": bool,    # True if large face consistently centered
            }
        """
        result = {
            "file": file_path,
            "has_face": False,
            "face_ratio": 0.0,
            "avg_face_size": 0.0,
            "is_talking_head": False,
        }
        
        if not self.face_cascade or not os.path.exists(file_path):
            return result

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return result
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
        frame_area = frame_w * frame_h
        
        if total_frames < 2:
            cap.release()
            return result

        # Sample frames evenly distributed through the clip
        step = max(1, total_frames // (sample_count + 1))
        face_frames = 0
        face_sizes = []
        face_center_offsets = []

        for i in range(1, sample_count + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, min(i * step, total_frames - 1))
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Downscale for speed
            small = cv2.resize(frame, (640, 360))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
            )
            
            if len(faces) > 0:
                face_frames += 1
                # Get the largest face
                largest = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest
                
                # Scale back to original resolution ratio
                face_area_ratio = (w * h) / (640 * 360)
                face_sizes.append(face_area_ratio)
                
                # How centered is the face? (0 = perfectly centered, 1 = at edge)
                center_x = (x + w / 2) / 640
                center_offset = abs(center_x - 0.5) * 2
                face_center_offsets.append(center_offset)

        cap.release()
        
        if sample_count > 0:
            result["face_ratio"] = face_frames / sample_count
            result["has_face"] = result["face_ratio"] > 0.3
        
        if face_sizes:
            result["avg_face_size"] = float(np.mean(face_sizes))
            avg_center_offset = float(np.mean(face_center_offsets))
            
            # "Talking head" = face appears in >60% of frames, is large, and centered
            result["is_talking_head"] = (
                result["face_ratio"] > 0.6 and
                result["avg_face_size"] > 0.02 and  # Face is at least 2% of frame
                avg_center_offset < 0.4              # Roughly centered
            )
        
        return result

    # ------------------------------------------------------------------
    #  Color Histogram — Group visually similar clips for cohesion
    # ------------------------------------------------------------------
    def compute_color_signature(self, file_path: str) -> Optional[np.ndarray]:
        """
        Computes a compact color histogram signature for a clip.
        Returns a 48-dimensional feature vector (16 bins × 3 channels in HSV).
        """
        if not os.path.exists(file_path):
            return None
        
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return None
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Sample 3 frames: 20%, 50%, 80% into the clip
        signatures = []
        
        for pct in [0.2, 0.5, 0.8]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames * pct))
            ret, frame = cap.read()
            if not ret:
                continue
            
            small = cv2.resize(frame, (160, 90))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            
            # 16 bins per channel
            hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
            hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()
            hist_v = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten()
            
            sig = np.concatenate([hist_h, hist_s, hist_v])
            sig = sig / (sig.sum() + 1e-8)  # Normalize
            signatures.append(sig)
        
        cap.release()
        
        if not signatures:
            return None
        
        return np.mean(signatures, axis=0)

    def color_distance(self, sig_a: np.ndarray, sig_b: np.ndarray) -> float:
        """Computes the chi-squared distance between two color signatures."""
        if sig_a is None or sig_b is None:
            return 1.0
        
        diff = sig_a - sig_b
        denom = sig_a + sig_b + 1e-8
        return float(0.5 * np.sum((diff ** 2) / denom))

    def sort_by_visual_similarity(self, clips: List[Dict]) -> List[Dict]:
        """
        Reorders clips to minimize visual jarring between adjacent cuts.
        Uses a greedy nearest-neighbor approach on color signatures.
        """
        if len(clips) <= 2:
            return clips
        
        # Compute signatures
        sigs = []
        for clip in clips:
            sig = self.compute_color_signature(clip.get("file", ""))
            sigs.append(sig)
        
        # Greedy nearest-neighbor ordering
        remaining = list(range(len(clips)))
        ordered = [remaining.pop(0)]
        
        while remaining:
            last = ordered[-1]
            last_sig = sigs[last]
            
            best_idx = min(remaining, key=lambda j: self.color_distance(last_sig, sigs[j]))
            remaining.remove(best_idx)
            ordered.append(best_idx)
        
        return [clips[i] for i in ordered]

    # ------------------------------------------------------------------
    #  Duplicate Detection — Never reuse the same segment twice
    # ------------------------------------------------------------------
    def compute_frame_hash(self, file_path: str, time_sec: float) -> str:
        """Computes a perceptual hash for a specific frame in a video."""
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return ""
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(time_sec * fps))
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return ""
        
        # Perceptual hash: resize to 8x8, convert to grayscale, threshold at mean
        small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (8, 8))
        mean_val = small.mean()
        bits = (small > mean_val).flatten()
        hash_bytes = np.packbits(bits).tobytes()
        return hashlib.md5(hash_bytes).hexdigest()

    def is_duplicate(self, file_path: str, start_sec: float) -> bool:
        """
        Checks if a specific clip segment has already been used.
        Returns True if it's a duplicate.
        """
        h = self.compute_frame_hash(file_path, start_sec + 1.0)
        if not h:
            return False
        
        if h in self._seen_hashes:
            return True
        
        self._seen_hashes.add(h)
        return False

    def reset_duplicates(self) -> None:
        """Clears the duplicate tracking set for a new edit session."""
        self._seen_hashes.clear()

    # ------------------------------------------------------------------
    #  Scene Complexity — Busy vs calm shot scoring
    # ------------------------------------------------------------------
    def analyze_complexity(self, file_path: str) -> float:
        """
        Analyzes how visually complex/busy a frame is using edge detection.
        Returns a score from 0.0 (simple, calm) to 1.0 (complex, busy).
        """
        if not os.path.exists(file_path):
            return 0.5
        
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return 0.5
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames * 0.5))
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return 0.5
        
        small = cv2.resize(frame, (320, 180))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        edge_ratio = float(np.count_nonzero(edges)) / edges.size
        # Normalize to 0-1 range (typical range is 0.02 - 0.20)
        complexity = min(1.0, edge_ratio / 0.15)
        
        return round(complexity, 3)

    # ------------------------------------------------------------------
    #  Batch Analysis — Full directory scan
    # ------------------------------------------------------------------
    def analyze_directory(self, folder_path: str) -> List[Dict]:
        """
        Performs full scene analysis on all video files in a directory.
        Returns enriched clip data with face, color, and complexity info.
        """
        if not folder_path or not os.path.exists(folder_path):
            return []
        
        video_exts = (".mp4", ".mov", ".mkv", ".m4v", ".avi", ".mts")
        files = [os.path.join(folder_path, f) for f in sorted(os.listdir(folder_path))
                 if f.lower().endswith(video_exts)]
        
        print(f"[SceneAnalyzer] Deep-analyzing {len(files)} files...")
        results = []
        
        for f in files:
            print(f"  [Scene] {os.path.basename(f)}...", end=" ")
            
            face_data = self.detect_faces_in_clip(f)
            complexity = self.analyze_complexity(f)
            color_sig = self.compute_color_signature(f)
            
            result = {
                "file": f,
                **face_data,
                "complexity": complexity,
                "color_signature": color_sig,
            }
            
            tags = []
            if face_data["is_talking_head"]:
                tags.append("talking-head")
            elif face_data["has_face"]:
                tags.append("has-face")
            if complexity > 0.6:
                tags.append("busy")
            elif complexity < 0.3:
                tags.append("calm")
            
            result["tags"] = tags
            print(f"[{', '.join(tags) or 'neutral'}] complexity={complexity:.2f}")
            
            results.append(result)
        
        return results
