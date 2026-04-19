"""
Render Engine — One-Click Export Automation

Configures render settings, queues jobs, and monitors progress using
DaVinci Resolve's delivery API:
  - Project.SetRenderSettings({settings})
  - Project.AddRenderJob()
  - Project.StartRendering()
  - Project.GetRenderJobStatus(jobId)
"""
import os
import time
from typing import Any, Dict, List, Optional

import config

# ---- Export Presets ----
EXPORT_PRESETS = {
    "youtube_1080": {
        "name": "YouTube 1080p",
        "FormatWidth":  1920,
        "FormatHeight": 1080,
        "FrameRate":    "24",
        "Format":       "mp4",
        "Codec":  "H265_NVIDIA" if os.name == "nt" else "H265",
        "Quality": 0,  # 0 = automatic/best
        "filename_suffix": "_youtube_1080p",
    },
    "youtube_4k": {
        "name": "YouTube 4K",
        "FormatWidth":  3840,
        "FormatHeight": 2160,
        "FrameRate":    "24",
        "Format":       "mp4",
        "Codec":  "H265_NVIDIA" if os.name == "nt" else "H265",
        "Quality": 0,
        "filename_suffix": "_youtube_4k",
    },
    "tiktok_vertical": {
        "name": "TikTok/Reels 9:16",
        "FormatWidth":  1080,
        "FormatHeight": 1920,
        "FrameRate":    "30",
        "Format":       "mp4",
        "Codec":  "H264",
        "Quality": 0,
        "filename_suffix": "_tiktok_9x16",
    },
    "instagram_square": {
        "name": "Instagram 1:1",
        "FormatWidth":  1080,
        "FormatHeight": 1080,
        "FrameRate":    "30",
        "Format":       "mp4",
        "Codec":  "H264",
        "Quality": 0,
        "filename_suffix": "_instagram_1x1",
    },
    "prores_master": {
        "name": "ProRes Master",
        "FormatWidth":  1920,
        "FormatHeight": 1080,
        "FrameRate":    "24",
        "Format":       "mov",
        "Codec":  "ProRes422HQ",
        "Quality": 0,
        "filename_suffix": "_master",
    },
}


class RenderEngine:
    """Automates the Deliver page workflow via Resolve's scripting API."""

    def __init__(self, controller: Any):
        self.controller = controller
        self.resolve = controller.resolve
        self.project = controller.project

    def configure_render(self, preset_key: str, output_dir: str,
                         filename: str = "auto_edit") -> bool:
        """
        Configures the render settings for a specific export preset.

        Args:
            preset_key: Key from EXPORT_PRESETS (e.g., "youtube_1080")
            output_dir: Directory to save the rendered file
            filename: Base filename (without extension)

        Returns:
            True if settings were applied successfully
        """
        if not self.resolve or not self.project:
            print(f"[Render/MOCK] Would configure {preset_key} render to {output_dir}")
            return True

        preset = EXPORT_PRESETS.get(preset_key)
        if not preset:
            print(f"[Render] ERROR: Unknown preset '{preset_key}'")
            return False

        os.makedirs(output_dir, exist_ok=True)
        full_filename = f"{filename}{preset['filename_suffix']}"

        settings = {
            "SelectAllFrames":    True,
            "TargetDir":          output_dir,
            "CustomName":         full_filename,
            "FormatWidth":        str(preset["FormatWidth"]),
            "FormatHeight":       str(preset["FormatHeight"]),
        }

        print(f"[Render] Configuring: {preset['name']} -> {output_dir}/{full_filename}")

        try:
            # Set format and codec first
            self.project.SetCurrentRenderFormatAndCodec(
                preset["Format"], preset["Codec"]
            )

            # Apply render settings
            result = self.project.SetRenderSettings(settings)
            if not result:
                print(f"[Render] Warning: SetRenderSettings returned False")
                return False

            return True
        except Exception as e:
            print(f"[Render] Error configuring render: {e}")
            return False

    def queue_render(self) -> Optional[str]:
        """Adds the current render configuration as a job. Returns the job ID."""
        if not self.resolve or not self.project:
            print("[Render/MOCK] Would add render job to queue")
            return "mock_job_id"

        try:
            job_id = self.project.AddRenderJob()
            if job_id:
                print(f"[Render] Job queued: {job_id}")
                return str(job_id)
            else:
                print("[Render] ERROR: AddRenderJob returned None")
                return None
        except Exception as e:
            print(f"[Render] Error queuing job: {e}")
            return None

    def start_rendering(self, job_ids: List[str] = None) -> bool:
        """
        Starts rendering all queued jobs (or specific job IDs).
        Returns True if rendering started successfully.
        """
        if not self.resolve or not self.project:
            print("[Render/MOCK] Would start rendering")
            return True

        try:
            if job_ids:
                result = self.project.StartRendering(job_ids)
            else:
                result = self.project.StartRendering()

            if result:
                print("[Render] Rendering started!")
                return True
            else:
                print("[Render] ERROR: StartRendering returned False")
                return False
        except Exception as e:
            print(f"[Render] Error starting render: {e}")
            return False

    def wait_for_completion(self, job_id: str, poll_interval: float = 2.0,
                           timeout: float = 600.0) -> bool:
        """
        Polls the render job status until completion or timeout.
        Prints progress updates.
        """
        if not self.resolve or not self.project:
            print("[Render/MOCK] Render complete (simulated)")
            return True

        start_time = time.time()
        last_pct = -1

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"[Render] TIMEOUT after {timeout}s")
                return False

            try:
                status = self.project.GetRenderJobStatus(job_id)
                if not status:
                    time.sleep(poll_interval)
                    continue

                job_status = status.get("JobStatus", "")
                completion_pct = status.get("CompletionPercentage", 0)

                if completion_pct != last_pct:
                    print(f"[Render] Progress: {completion_pct}% ({job_status})")
                    last_pct = completion_pct

                if job_status == "Complete":
                    print(f"[Render] SUCCESS: Render complete in {elapsed:.1f}s")
                    return True
                elif job_status in ("Failed", "Cancelled"):
                    error = status.get("Error", "Unknown error")
                    print(f"[Render] FAILED: {error}")
                    return False

            except Exception as e:
                print(f"[Render] Status poll error: {e}")

            time.sleep(poll_interval)

    def render_preset(self, preset_key: str, output_dir: str,
                      filename: str = "auto_edit") -> bool:
        """
        High-level: Configure, queue, render, and wait for a single preset.
        Returns True on success.
        """
        print(f"\n[Render] === Starting {EXPORT_PRESETS.get(preset_key, {}).get('name', preset_key)} ===")

        if not self.configure_render(preset_key, output_dir, filename):
            return False

        job_id = self.queue_render()
        if not job_id:
            return False

        if not self.start_rendering([job_id]):
            return False

        return self.wait_for_completion(job_id)

    def render_multi(self, preset_keys: List[str], output_dir: str,
                     filename: str = "auto_edit") -> Dict[str, bool]:
        """
        Renders multiple presets sequentially.
        Returns a dict of {preset_key: success_bool}.
        """
        results = {}
        for key in preset_keys:
            results[key] = self.render_preset(key, output_dir, filename)
        return results

    def get_available_formats(self) -> Dict:
        """Returns all render formats and codecs supported by this Resolve installation."""
        if not self.resolve or not self.project:
            return {"mp4": ["H264", "H265"], "mov": ["ProRes422HQ"]}

        try:
            formats = self.project.GetRenderFormats()
            result = {}
            for fmt_name, fmt_ext in formats.items():
                codecs = self.project.GetRenderCodecs(fmt_ext)
                result[fmt_ext] = list(codecs.keys()) if codecs else []
            return result
        except Exception as e:
            print(f"[Render] Error fetching formats: {e}")
            return {}
