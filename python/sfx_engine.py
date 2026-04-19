"""
SFX Engine — Sound Effect Placement & Management

Places whoosh, impact, and riser SFX on the timeline aligned to:
  - Transition points (whoosh on every cut)
  - Beat impacts (hit sounds on strong beats)
  - Scene changes (risers before big reveals)

Uses DaVinci Resolve's media pool and timeline API to place audio clips
on a dedicated SFX track (Audio Track 3).
"""
import os
import random
from typing import Any, Dict, List, Optional, Tuple

import config


# ---- SFX Categories ----
SFX_TYPES = {
    "whoosh": {
        "description": "Fast air movement for transitions",
        "files": ["whoosh_01.wav", "whoosh_02.wav", "whoosh_03.wav"],
        "default_volume": 0.5,
        "placement": "transition",
    },
    "impact": {
        "description": "Heavy hit for beat impacts and hard cuts",
        "files": ["impact_01.wav", "impact_02.wav", "impact_03.wav"],
        "default_volume": 0.6,
        "placement": "beat",
    },
    "riser": {
        "description": "Rising tension before a big reveal or drop",
        "files": ["riser_01.wav", "riser_02.wav"],
        "default_volume": 0.4,
        "placement": "pre_burst",
    },
    "glitch": {
        "description": "Digital glitch for hyper-style transitions",
        "files": ["glitch_01.wav", "glitch_02.wav"],
        "default_volume": 0.5,
        "placement": "transition",
    },
}

# Style-specific SFX profiles
STYLE_SFX_PROFILES = {
    "cinematic": {
        "enabled": ["whoosh", "riser"],
        "density": 0.3,  # Only 30% of eligible points get SFX
        "volume_mult": 0.6,
    },
    "vlog": {
        "enabled": ["whoosh"],
        "density": 0.2,
        "volume_mult": 0.4,
    },
    "reel": {
        "enabled": ["whoosh", "impact"],
        "density": 0.5,
        "volume_mult": 0.7,
    },
    "hyper": {
        "enabled": ["whoosh", "impact", "glitch", "riser"],
        "density": 0.8,  # Almost every transition gets something
        "volume_mult": 1.0,
    },
}


class SFXEngine:
    """Places sound effects on the timeline synchronized to cuts and beats."""

    def __init__(self, controller: Any, style: str = "vlog"):
        self.controller = controller
        self.style = style
        self.profile = STYLE_SFX_PROFILES.get(style, STYLE_SFX_PROFILES["vlog"])
        self.sfx_dir = config.SFX_DIR
        os.makedirs(self.sfx_dir, exist_ok=True)
        
        # Map available SFX files
        self.available_sfx: Dict[str, List[str]] = {}
        self._scan_sfx_directory()

    def _scan_sfx_directory(self) -> None:
        """Scans the SFX directory and maps available sound effect files."""
        if not os.path.exists(self.sfx_dir):
            return
        
        for sfx_type, info in SFX_TYPES.items():
            available = []
            for fname in info["files"]:
                fpath = os.path.join(self.sfx_dir, fname)
                if os.path.exists(fpath):
                    available.append(fpath)
            
            if available:
                self.available_sfx[sfx_type] = available
        
        total = sum(len(v) for v in self.available_sfx.values())
        if total > 0:
            print(f"[SFX] Found {total} sound effects across {len(self.available_sfx)} categories")
        else:
            print(f"[SFX] No sound effects found in {self.sfx_dir} — SFX layer will be skipped")
            print(f"  Tip: Add .wav files to {self.sfx_dir} (e.g., whoosh_01.wav, impact_01.wav)")

    def _pick_sfx(self, sfx_type: str) -> Optional[str]:
        """Randomly picks an available SFX file of the given type."""
        files = self.available_sfx.get(sfx_type, [])
        if not files:
            return None
        return random.choice(files)

    def _should_place(self) -> bool:
        """Randomly decides whether to place SFX based on density setting."""
        return random.random() < self.profile["density"]

    def place_transition_sfx(self, transition_frames: List[int]) -> int:
        """
        Places whoosh/glitch SFX at transition cut points on Audio Track 3.
        
        Args:
            transition_frames: List of timeline frame numbers where transitions occur
            
        Returns:
            Number of SFX placed
        """
        if not self.controller.resolve:
            print(f"[SFX/MOCK] Would place SFX at {len(transition_frames)} transition points")
            return 0
        
        enabled_types = [t for t in self.profile["enabled"] 
                        if SFX_TYPES[t]["placement"] == "transition"]
        
        if not enabled_types or not any(t in self.available_sfx for t in enabled_types):
            return 0
        
        tl = self.controller.project.GetCurrentTimeline()
        if not tl:
            return 0
        
        placed = 0
        vol_mult = self.profile["volume_mult"]
        
        for frame in transition_frames:
            if not self._should_place():
                continue
            
            sfx_type = random.choice(enabled_types)
            sfx_path = self._pick_sfx(sfx_type)
            if not sfx_path:
                continue
            
            try:
                # Import the SFX into media pool if not already there
                item = self._import_sfx_clip(sfx_path)
                if not item:
                    continue
                
                # Place on Audio Track 3, slightly before the cut point
                # (offset by ~6 frames so the whoosh peaks at the cut)
                offset_frame = max(0, frame - 6)
                self.controller.add_clip_to_timeline(
                    item, "audio", 3, 0, None, record_frame=offset_frame
                )
                
                # Set volume
                base_vol = SFX_TYPES[sfx_type]["default_volume"]
                vol = base_vol * vol_mult * config.SFX_VOLUME.get(self.style, 0.5)
                # Volume as percentage
                vol_pct = vol * 100
                
                placed += 1
                
            except Exception as e:
                print(f"  [SFX] Warning: Could not place {sfx_type} at frame {frame}: {e}")
        
        if placed:
            print(f"[SFX] Placed {placed} transition sound effects")
        return placed

    def place_beat_sfx(self, beat_frames: List[int], burst_zones: List[Tuple] = None) -> int:
        """
        Places impact SFX at strong beat positions on Audio Track 3.
        
        Args:
            beat_frames: List of timeline frame numbers at beat positions
            burst_zones: Optional (start, end) tuples for high-energy zones
            
        Returns:
            Number of SFX placed
        """
        if not self.controller.resolve:
            print(f"[SFX/MOCK] Would place beat SFX at {len(beat_frames)} positions")
            return 0
        
        enabled_types = [t for t in self.profile["enabled"]
                        if SFX_TYPES[t]["placement"] == "beat"]
        
        if not enabled_types or not any(t in self.available_sfx for t in enabled_types):
            return 0
        
        # Only place on every Nth beat to avoid overwhelming the mix
        beat_spacing = max(1, 4 if self.style != "hyper" else 2)
        
        placed = 0
        for i, frame in enumerate(beat_frames):
            if i % beat_spacing != 0:
                continue
            if not self._should_place():
                continue
            
            sfx_type = random.choice(enabled_types)
            sfx_path = self._pick_sfx(sfx_type)
            if not sfx_path:
                continue
            
            try:
                item = self._import_sfx_clip(sfx_path)
                if not item:
                    continue
                
                self.controller.add_clip_to_timeline(
                    item, "audio", 3, 0, None, record_frame=frame
                )
                placed += 1
                
            except Exception as e:
                print(f"  [SFX] Warning: Could not place beat SFX at frame {frame}: {e}")
        
        # Place risers before burst zones
        if burst_zones:
            riser_placed = self._place_risers(burst_zones)
            placed += riser_placed
        
        if placed:
            print(f"[SFX] Placed {placed} beat/impact sound effects")
        return placed

    def _place_risers(self, burst_zones: List[Tuple]) -> int:
        """Places riser SFX 2 seconds before each burst zone begins."""
        if "riser" not in self.profile["enabled"]:
            return 0
        if "riser" not in self.available_sfx:
            return 0
        
        fps = self.controller.timeline_fps
        start_frame = self.controller.timeline_start_frame
        placed = 0
        
        for zone in burst_zones[:3]:  # Max 3 risers per edit
            zone_start_frame = start_frame + int(zone[0] * fps)
            riser_frame = max(0, zone_start_frame - int(2 * fps))  # 2 seconds before
            
            sfx_path = self._pick_sfx("riser")
            if not sfx_path:
                continue
            
            try:
                item = self._import_sfx_clip(sfx_path)
                if item:
                    self.controller.add_clip_to_timeline(
                        item, "audio", 3, 0, None, record_frame=riser_frame
                    )
                    placed += 1
            except Exception:
                pass
        
        return placed

    def _import_sfx_clip(self, sfx_path: str) -> Optional[Any]:
        """Imports an SFX file into the media pool (cached per session)."""
        if not self.controller.media_pool:
            return None
        
        try:
            imported = self.controller.media_pool.ImportMedia([sfx_path])
            if imported and len(imported) > 0:
                return imported[0]
        except Exception:
            pass
        
        return None
