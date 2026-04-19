"""
Color Grader — Automatic Cinematic Look Engine

Applies style-appropriate color grades to every clip on the timeline using
DaVinci Resolve's native grading API:
  - SetLUT(nodeIndex, lutPath)     — Film emulation / creative LUTs
  - SetCDL({...})                  — Slope/Offset/Power corrections
  - ApplyGradeFromDRX(path, mode)  — Full DRX grade presets
  - CopyGrades([targets])          — Propagate a hero grade
"""
import os
import cv2
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

import config


# ---- Style-to-Grade Mapping ----
# Each style maps to a CDL correction profile and optional LUT.

STYLE_GRADES = {
    "cinematic": {
        "description": "Warm film emulation with lifted shadows and rolled-off highlights",
        "cdl": {
            "Slope":      [1.05, 1.00, 0.92],   # Warm highlights (push red, pull blue)
            "Offset":     [0.01, 0.005, -0.01],  # Slight warm lift in shadows
            "Power":      [0.95, 0.95, 1.05],    # Gentle contrast curve
            "Saturation": 0.90                     # Slightly desaturated for film feel
        },
        "lut_name": "cinematic_film.cube",
    },
    "vlog": {
        "description": "Clean, bright, natural with slight warmth",
        "cdl": {
            "Slope":      [1.02, 1.02, 1.00],
            "Offset":     [0.005, 0.005, 0.0],
            "Power":      [1.0, 1.0, 1.0],
            "Saturation": 0.95
        },
        "lut_name": None,  # No creative LUT — just CDL correction
    },
    "reel": {
        "description": "Punchy contrast with vivid but controlled saturation",
        "cdl": {
            "Slope":      [1.08, 1.05, 1.00],
            "Offset":     [0.0, 0.0, -0.005],
            "Power":      [0.88, 0.90, 1.00],     # Strong contrast
            "Saturation": 1.15                      # Boosted saturation
        },
        "lut_name": None,
    },
    "hyper": {
        "description": "Aggressive orange-teal split-tone with crushed blacks",
        "cdl": {
            "Slope":      [1.15, 1.02, 0.85],     # Strong orange push
            "Offset":     [0.02, 0.0, -0.03],      # Orange shadows, teal lift
            "Power":      [0.80, 0.85, 1.10],      # Crushed blacks, boosted contrast
            "Saturation": 1.25                       # High saturation
        },
        "lut_name": None,
    },
}


class ColorGrader:
    """Applies automatic color grading to timeline clips based on editing style."""

    def __init__(self, style: str = "vlog"):
        self.style = style
        self.grade_profile = STYLE_GRADES.get(style, STYLE_GRADES["vlog"])
        self.lut_dir = os.path.join(config.BASE_DIR, "assets", "luts")
        os.makedirs(self.lut_dir, exist_ok=True)

    def get_lut_path(self) -> Optional[str]:
        """Returns the absolute path to the style's LUT file, if one exists."""
        lut_name = self.grade_profile.get("lut_name")
        if not lut_name:
            return None
        lut_path = os.path.join(self.lut_dir, lut_name)
        if os.path.exists(lut_path):
            return lut_path
        return None

    def analyze_clip_exposure(self, file_path: str) -> Dict[str, float]:
        """
        Analyzes a video clip's first frame to compute exposure correction values.
        Returns adjustment multipliers for brightness and contrast.
        """
        if not file_path or not os.path.exists(file_path):
            return {"brightness_offset": 0.0, "contrast_mult": 1.0}

        try:
            cap = cv2.VideoCapture(file_path)
            # Sample from 10% into the clip to avoid slates/black frames
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(1, int(total_frames * 0.1)))

            ret, frame = cap.read()
            cap.release()
            if not ret:
                return {"brightness_offset": 0.0, "contrast_mult": 1.0}

            # Convert to LAB for perceptual brightness analysis
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]

            mean_l = float(np.mean(l_channel))
            std_l = float(np.std(l_channel))

            # Target: mean luminance ~128 (middle gray in LAB)
            # Compute offset needed to reach target
            target_mean = 128.0
            brightness_offset = (target_mean - mean_l) / 255.0 * 0.1  # Scale to CDL range

            # Target: std dev ~45 for good contrast
            target_std = 45.0
            contrast_mult = target_std / max(std_l, 1.0)
            contrast_mult = max(0.7, min(contrast_mult, 1.4))  # Clamp to reasonable range

            return {
                "brightness_offset": round(brightness_offset, 4),
                "contrast_mult": round(contrast_mult, 3)
            }
        except Exception:
            return {"brightness_offset": 0.0, "contrast_mult": 1.0}

    def compute_cdl_for_clip(self, file_path: str = None) -> Dict:
        """
        Computes the final CDL values for a clip by combining:
        1. The style's base CDL profile
        2. Per-clip exposure correction (if file_path is provided)
        """
        base = self.grade_profile["cdl"]
        cdl = {
            "Slope":      list(base["Slope"]),
            "Offset":     list(base["Offset"]),
            "Power":      list(base["Power"]),
            "Saturation": base["Saturation"]
        }

        # Apply per-clip exposure correction
        if file_path:
            exposure = self.analyze_clip_exposure(file_path)
            # Adjust offset for brightness
            for i in range(3):
                cdl["Offset"][i] += exposure["brightness_offset"]
            # Adjust power for contrast
            for i in range(3):
                cdl["Power"][i] *= exposure["contrast_mult"]
                cdl["Power"][i] = round(max(0.5, min(cdl["Power"][i], 1.5)), 3)

        return cdl

    def grade_timeline(self, controller: Any, placed_clips_info: List[Tuple[str, str]]) -> None:
        """
        Applies color grading to all clips on the current timeline.

        Args:
            controller: ResolveController instance
            placed_clips_info: List of (pool_name, file_path) tuples for each clip
        """
        if not controller.resolve:
            print(f"[ColorGrader/MOCK] Would apply '{self.style}' grade to {len(placed_clips_info)} clips")
            return

        tl = controller.project.GetCurrentTimeline()
        if not tl:
            print("[ColorGrader] ERROR: No active timeline")
            return

        v1_items = tl.GetItemListInTrack("video", 1)
        if not v1_items:
            print("[ColorGrader] No video items on track 1")
            return

        print(f"[ColorGrader] Applying '{self.style}' grade ({self.grade_profile['description']})")

        # Step 1: Apply LUT if available
        lut_path = self.get_lut_path()
        lut_applied = False
        if lut_path:
            print(f"  [LUT] Applying {os.path.basename(lut_path)} to all clips...")
            for item in v1_items:
                try:
                    # nodeIndex is 1-based in the Resolve API
                    item.SetLUT(1, lut_path)
                    lut_applied = True
                except Exception as e:
                    print(f"  [LUT] Warning: Could not apply LUT: {e}")
                    break

        # Step 2: Apply CDL corrections
        graded_count = 0
        hero_item = None

        for i, item in enumerate(v1_items):
            # Get the source file path for exposure analysis
            file_path = None
            if i < len(placed_clips_info):
                file_path = placed_clips_info[i][1]

            cdl = self.compute_cdl_for_clip(file_path)

            try:
                item.SetCDL({
                    "NodeIndex": "1",
                    "Slope":      f"{cdl['Slope'][0]} {cdl['Slope'][1]} {cdl['Slope'][2]}",
                    "Offset":     f"{cdl['Offset'][0]} {cdl['Offset'][1]} {cdl['Offset'][2]}",
                    "Power":      f"{cdl['Power'][0]} {cdl['Power'][1]} {cdl['Power'][2]}",
                    "Saturation": str(cdl["Saturation"])
                })
                graded_count += 1

                if hero_item is None:
                    hero_item = item  # First successfully graded clip becomes the hero

            except Exception as e:
                print(f"  [CDL] Warning: Could not apply CDL to clip {i}: {e}")

        # Step 3: Copy hero grade to ensure consistency (fallback if CDL failed on some)
        if hero_item and graded_count < len(v1_items):
            try:
                ungraded = [item for j, item in enumerate(v1_items) if j >= graded_count]
                if ungraded:
                    hero_item.CopyGrades(ungraded)
                    print(f"  [Grade Copy] Propagated hero grade to {len(ungraded)} remaining clips")
            except Exception as e:
                print(f"  [Grade Copy] Warning: {e}")

        status = "with LUT + CDL" if lut_applied else "with CDL only"
        print(f"[ColorGrader] Done: {graded_count}/{len(v1_items)} clips graded {status}")
