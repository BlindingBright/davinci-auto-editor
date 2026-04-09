import os
import numpy as np
from typing import List, Tuple, Optional

class MusicAnalyzer:
    def __init__(self) -> None:
        self.librosa = None

    def _load_librosa(self) -> None:
        if self.librosa is None:
            print("[AI] Loading librosa for beat detection (this takes a moment)...")
            import librosa
            self.librosa = librosa

    def analyze_beats(self, file_path: str) -> Tuple[float, List[float]]:
        """
        Analyzes an audio file to find the BPM and a list of beat timestamps.
        Returns (BPM, [beat_timestamps]).
        """
        if not file_path or not os.path.exists(file_path):
            return 120.0, [], []

        try:
            self._load_librosa()
            # Load only first 60s for performance
            y, sr = self.librosa.load(file_path, duration=60)
            
            # 1. Standard tempo and rhythm grid
            tempo, beat_frames = self.librosa.beat.beat_track(y=y, sr=sr)
            beat_times = self.librosa.frames_to_time(beat_frames, sr=sr).tolist()
            
            # 2. Onset Detection (Snappy Impacts)
            # Find frames with high onset strength (drums, etc)
            onset_frames = self.librosa.onset.onset_detect(y=y, sr=sr, wait=5, pre_avg=5, post_avg=5, pre_max=5, post_max=5)
            onsets = self.librosa.frames_to_time(onset_frames, sr=sr).tolist()
            
            # 3. Burst Zone Detection (High Intensity)
            burst_zones = []
            if len(onsets) > 5:
                # Calculate window density
                for i in range(len(onsets) - 5):
                    # If 5 onsets happen within 2 seconds, it's a burst zone
                    if onsets[i+4] - onsets[i] < 2.0:
                        burst_zones.append((onsets[i], onsets[i+4]))
            
            # librosa.beat.beat_track returns tempo as a numpy array in newer versions
            # We flatten and take the first value in case multiple bpm candidates were returned
            tempo_float = float(np.array(tempo).flatten()[0])
            print(f"  Detected BPM: {tempo_float:.1f} | Beats: {len(beat_times)} | Impacts: {len(onsets)} | Bursts: {len(burst_zones)}")
            return tempo_float, beat_times, onsets, burst_zones
        except Exception as e:
            import traceback
            print(f"[AI] Rhythmic analysis failed: {e}")
            traceback.print_exc()
            return 120.0, [], [], []

    def get_nearest_beat(self, current_time: float, beat_times: List[float], min_interval: float = 2.0) -> float:
        """Finds the best cut point near the current_time that aligns with a beat."""
        if not beat_times:
            return current_time + min_interval
            
        # Find beats beyond the min threshold
        valid_beats = [b for b in beat_times if b >= current_time + min_interval]
        if not valid_beats:
            # If no beats found in preview, fallback to BPM-based grid
            return current_time + min_interval
            
        # Return the earliest beat that satisfies the gap
        return valid_beats[0]
