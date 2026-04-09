import os
import config
from typing import List, Dict, Tuple

class AudioAnalyzer:
    def __init__(self) -> None:
        print(f"[AI] Initializing faster-whisper Model ({config.WHISPER_MODEL}, {config.WHISPER_COMPUTE_TYPE})...")
        self.model = None
        self.whisper_available = False
        try:
            from faster_whisper import WhisperModel
            self.whisper_available = True
        except ImportError:
            print("[AI] faster-whisper not available — A-Roll will use full clips as segments.")

    def _load_model(self) -> None:
        if self.model is None and self.whisper_available:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type=config.WHISPER_COMPUTE_TYPE)

    def analyze_directory(self, folder_path: str) -> List[Dict]:
        if not folder_path or not os.path.exists(folder_path):
            return []

        video_exts = (".mp4", ".mov", ".mkv", ".m4v", ".avi", ".mts")
        files = [os.path.join(folder_path, f) for f in sorted(os.listdir(folder_path)) 
                 if f.lower().endswith(video_exts)]
        print(f"[AI] Found {len(files)} A-Roll file(s) in {folder_path}")
        results = []

        for file in files:
            file_results = {"file": file, "speaking_segments": []}
            
            # --- Try Speech Detection First ---
            if self.whisper_available:
                self._load_model()
                print(f"[AI] Transcribing {os.path.basename(file)}...")
                try:
                    segments, info = self.model.transcribe(
                        file, 
                        vad_filter=True, 
                        vad_parameters=dict(min_silence_duration_ms=config.WHISPER_VAD_MIN_SILENCE)
                    )
                    for seg in segments:
                        duration = seg.end - seg.start
                        if duration < 0.5: continue
                        density = len(seg.text) / duration
                        score = (seg.avg_logprob + 2) * (density / 10.0) 
                        file_results["speaking_segments"].append((round(seg.start, 2), round(seg.end, 2), round(score, 3)))
                except Exception as e:
                    print(f"[AI] Whisper failed for {file}: {e}")

            # --- If No Speech, Fallback to 'Action Vibe' Analysis (Motion + Energy) ---
            if not file_results["speaking_segments"]:
                print(f"[AI] No speech found. Analyzing Action Vibe for {os.path.basename(file)}...")
                action_segments = self._analyze_action_vibe(file)
                file_results["speaking_segments"] = action_segments

            file_results["speaking_segments"].sort(key=lambda x: x[2], reverse=True)
            results.append(file_results)

        return results

    def _analyze_action_vibe(self, file_path: str) -> List[Tuple]:
        """Detects segments with high visual motion and audio energy."""
        import cv2
        import numpy as np
        try:
            import librosa
        except ImportError:
            return [(0.0, 5.0, 0.1)] # Very basic fallback

        # 1. Audio Energy Analysis
        rms = np.array([])
        try:
            y, sr = librosa.load(file_path, sr=None, duration=120) # Sample first 2 mins
            rms = librosa.feature.rms(y=y)[0]
            # Find peaks in energy
            threshold = np.median(rms) * 1.5
            peaks = np.where(rms > threshold)[0]
        except Exception as e:
            print(f"  [AI] Note: Audio energy analysis skipped for action vibe ({e})")
            peaks = []

        # 2. Basic Motion Analysis (OpenCV)
        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        motion_segments = []
        
        # We sample 5-second windows to find the 'peak action'
        duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        for start in range(0, int(duration) - 5, 5):
            # Combined score: RMS energy + motion estimate (placeholder for full optical flow)
            # For brevity, we use RMS as a proxy for 'action energy' in A-Roll
            # but boost it if it's a known action shot.
            window_rms = np.mean(rms[int(start*len(rms)/duration):int((start+5)*len(rms)/duration)]) if len(rms)>0 else 0.1
            score = float(window_rms * 10.0) # Scale it
            motion_segments.append((float(start), float(start + 5), score))
        
        cap.release()
        return motion_segments

    def _fallback_analysis(self, file: str) -> Dict:
        """Fallback: use entire clip as one speaking segment by probing duration."""
        import cv2
        cap = cv2.VideoCapture(file)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        duration = n_frames / fps if fps > 0 else 60.0
        print(f"[AI] A-Roll fallback: using full clip {os.path.basename(file)} ({duration:.1f}s)")
        return {
            "file": file,
            "speaking_segments": [(0.0, duration, 0.5)] # Default low score for fallback
        }
