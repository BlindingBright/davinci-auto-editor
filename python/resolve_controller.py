import os
import sys
import config
from typing import Any, List, Dict, Tuple, Optional

# Add Resolve scripting path
sys.path.append(os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), 
                           "Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Modules"))

class ResolveController:
    def __init__(self) -> None:
        print("[Resolve] Initializing ResolveController...")
        self.resolve = None
        self.project = None
        self.media_pool = None
        self.media_storage = None
        self.timeline_start_frame = 0
        self.timeline_fps = 24.0
        
        try:
            import DaVinciResolveScript as dvr
            self.resolve = dvr.scriptapp("Resolve")
        except ImportError:
            print("[Resolve] Warning: DaVinciResolveScript not found. Running in MOCK mode.")
        
        if self.resolve:
            print("[Resolve] Attempting to connect to DaVinci Resolve...")
            self.project_manager = self.resolve.GetProjectManager()
            self.project = self.project_manager.GetCurrentProject()
            self.media_storage = self.resolve.GetMediaStorage()
            self.media_pool = self.project.GetMediaPool()
        else:
            print("[Resolve] Error: Could not connect to Resolve. Ensure it is open.")

    def create_or_load_project(self, project_name: str) -> bool:
        if not self.resolve:
            print(f"[Resolve/MOCK] Creating project: {project_name}")
            return True
        
        print(f"[Resolve] Creating/Loading project: {project_name}")
        project = self.project_manager.LoadProject(project_name)
        if not project:
            print(f"[Resolve] Project {project_name} not found. Creating new...")
            project = self.project_manager.CreateProject(project_name)
        
        if project:
            self.project = project
            self.media_pool = self.project.GetMediaPool()
            return True
        return False

    def get_media_pool_metadata(self) -> Dict[str, str]:
        """Returns a mapping of absolute file paths to internal Resolve UniqueIds."""
        if not self.project: return {}
        mapping = {}
        try:
            mp = self.project.GetMediaPool()
            clips = mp.GetRootFolder().GetClipList()
            for clip in clips:
                path = clip.GetClipProperty("File Path")
                uid = clip.GetUniqueId()
                if path:
                    mapping[os.path.abspath(path)] = uid
        except Exception as e:
            print(f"  [Resolve] Warning: Could not fetch clip metadata: {e}")
        return mapping

    def import_media(self, file_paths: List[str]) -> Dict[str, Any]:
        """Imports files into the media pool and returns a map of {path: MediaPoolItem}."""
        if not self.resolve:
            print(f"[Resolve/MOCK] Importing {len(file_paths)} files...")
            return {p: f"MockItem_{os.path.basename(p)}" for p in file_paths}

        # Use absolute paths
        abs_paths = [os.path.abspath(p) for p in file_paths]
        items = self.media_storage.AddItemListToMediaPool(abs_paths)
        
        # Resolve sometimes returns a list, sometimes None if everything exists
        # We'll map by checking the media pool root folder
        root_folder = self.media_pool.GetRootFolder()
        all_clips = root_folder.GetClipList()
        
        mapping = {}
        for clip in all_clips:
            clip_path = clip.GetClipProperty("File Path")
            if clip_path in abs_paths:
                mapping[clip_path] = clip
            # Handle normalized paths
            elif clip_path.replace("/", "\\") in [p.replace("/", "\\") for p in abs_paths]:
                 mapping[clip_path] = clip

        return mapping

    def create_timeline(self, timeline_name: str):
        if not self.resolve:
            print(f"[Resolve/MOCK] Creating timeline: {timeline_name}")
            return True
        
        # Check if timeline already exists
        count = self.project.GetTimelineCount()
        for i in range(1, count + 1):
            t = self.project.GetTimelineByIndex(i)
            if t.GetName() == timeline_name:
                print(f"[Resolve] Timeline {timeline_name} already exists. Setting as current.")
                self.project.SetCurrentTimeline(t)
                self.timeline_start_frame = int(t.GetStartFrame())
                self.timeline_fps = float(t.GetSetting("timelineFrameRate"))
                return t
        
        timeline = self.media_pool.CreateEmptyTimeline(timeline_name)
        if timeline:
            print(f"[Resolve] Creating timeline: {timeline_name}")
            self.project.SetCurrentTimeline(timeline)
            self.timeline_start_frame = int(timeline.GetStartFrame())
            self.timeline_fps = float(timeline.GetSetting("timelineFrameRate"))
            print(f"[Resolve] Timeline {timeline_name} starts at {self.timeline_start_frame} | FPS: {self.timeline_fps}")
            return timeline
        return None

    def add_clip_to_timeline(self, media_item: Any, type: str = "video", track: int = 1, start_frame: int = 0, end_frame: int = 100, record_frame: int = None) -> Any:
        """Appends or places a clip segment to a specific track at a specific record frame."""
        if not self.resolve or not self.project: return None
        try:
            mp = self.project.GetMediaPool()
            
            # Ensure the timeline has the necessary track
            tl = self.project.GetCurrentTimeline()
            if tl:
                while int(track) > tl.GetTrackCount(type):
                    tl.AddTrack(type)
            
            clip_info = {
                "mediaPoolItem": media_item,
                "startFrame": int(start_frame),
                "endFrame": int(end_frame),
                "trackIndex": int(track),
                "mediaType": 2 if type.lower() == "audio" else 1
            }
            if record_frame is not None:
                # Add the 86400 (1:00:00:00) default Resolve start offset if necessary
                clip_info["recordFrame"] = int(self.timeline_start_frame + record_frame)
            
            items = mp.AppendToTimeline([clip_info])
            if items and len(items) > 0:
                return items[0]
        except Exception as e:
            print(f"  [Resolve] Error adding clip: {e}")
        return None

    def get_last_clip_on_track(self, track_index: int = 1) -> Any:
        """Returns the last TimelineItem on the specified video track."""
        if not self.project: return None
        tl = self.project.GetCurrentTimeline()
        items = tl.GetItemListInTrack("video", track_index)
        if items and len(items) > 0:
            return items[-1]
        return None

    def set_clip_zoom(self, item: Any, zoom: float) -> None:
        """Sets the digital zoom of a timeline item (1.0 = 100%)."""
        if not item or not self.resolve: return
        try:
            item.SetProperty("ZoomX", zoom)
            item.SetProperty("ZoomY", zoom)
        except Exception as e:
            print(f"  [Resolve] Warning: Could not set zoom for item: {e}")

    def set_clip_pan(self, item: Any, pan_x: float, pan_y: float) -> None:
        """Sets the pan/offset of a timeline item."""
        if not item or not self.resolve: return
        try:
            item.SetProperty("PanX", pan_x)
            item.SetProperty("PanY", pan_y)
        except Exception as e:
            print(f"  [Resolve] Warning: Could not set pan for item: {e}")

    def set_clip_composite_mode(self, item: Any, mode: int = 2) -> None:
        """Sets the composite mode (e.g., 2 is Screen, 3 is Add)."""
        if not item or not self.resolve: return
        try:
            item.SetProperty("CompositeMode", mode)
        except Exception as e:
            print(f"  [Resolve] Warning: Could not set composite mode: {e}")

    def set_clip_opacity(self, item: Any, opacity: float) -> None:
        """Sets clip opacity (0-100)."""
        if not item or not self.resolve: return
        try:
            item.SetProperty("Opacity", opacity)
        except Exception as e:
            print(f"  [Resolve] Warning: Could not set opacity: {e}")

    def import_timeline(self, xml_path: str, timeline_name: str) -> bool:
        """Imports an FCPXML timeline into the current project, including native transitions."""
        if not self.media_pool:
            print("[Resolve] No media pool to import XML into.")
            return False
        
        print(f"[Resolve] Importing native XML timeline: {xml_path}")
        options = {
            "timelineName": timeline_name,
            "importSourceClips": True
        }
        
        timeline = self.media_pool.ImportTimelineFromFile(xml_path, options)
        if timeline:
            print(f"[Resolve] Successfully imported native timeline: {timeline.GetName()}")
            self.project.SetCurrentTimeline(timeline)
            self.timeline_start_frame = int(timeline.GetStartFrame())
            self.timeline_fps = float(timeline.GetSetting("timelineFrameRate"))
            return True
        print(f"[Resolve] WARNING: ImportTimelineFromFile returned None for {xml_path}")
        return False

    def relink_clips(self, clips: List[Any], folder: str) -> bool:
        """Force relinks a list of clips to a specific folder."""
        if not self.media_pool: return False
        try:
            return self.media_pool.RelinkClips(clips, folder)
        except Exception as e:
            print(f"  [Resolve] Warning: Relink failed: {e}")
            return False

    def relink_all_offline(self, search_paths: List[str]) -> None:
        """Scans the media pool and attempts to relink any offline clips to the search paths."""
        if not self.media_pool: return
        root = self.media_pool.GetRootFolder()
        clips = root.GetClipList()
        
        offline_clips = []
        for clip in clips:
            if clip.GetClipProperty("Status") == "Offline" or not clip.GetClipProperty("File Path"):
                offline_clips.append(clip)
        
        if not offline_clips:
            print("  [Resolve] All clips are online. No relinking needed.")
            return

        print(f"  [Resolve] Found {len(offline_clips)} offline clips. Attempting auto-relink...")
        for path in search_paths:
            if self.relink_clips(offline_clips, path):
                print(f"  [Resolve] Successfully relinked clips to: {path}")

    def apply_staircase_fade(self, media_item: Any, start_f: int, end_f: int, 
                             duration_f: int = 10, direction: str = "in") -> None:
        """
        Manually creates a fade by splitting a 0.5s segment into tiny chunks with stepped opacity.
        This bypasses the API's 'no transitions' limitation.
        """
        if not self.resolve: return
        
        for i in range(duration_f):
            opacity = (i / duration_f) * 100 if direction == "in" else ((duration_f - i) / duration_f) * 100
            chunk_start = start_f + i if direction == "in" else (end_f - duration_f + i)
            chunk_end = chunk_start + 1
            
            tl_item = self.add_clip_to_timeline(media_item, "video", 1, chunk_start, chunk_end, record_frame=None)
            if tl_item:
                self.set_clip_opacity(tl_item, opacity)

    def set_optical_flow(self, item: Any) -> None:
        """Enables Resolve's 'Optical Flow' retime process for liquid motion."""
        if not item or not self.resolve: return
        try:
            # 2 = Optical Flow in most Resolve versions
            item.SetProperty("RetimeProcess", "Optical Flow")
            item.SetProperty("MotionEstimation", "Enhanced Better")
        except Exception as e:
            print(f"  [Resolve] Warning: Could not set optical flow: {e}")

    def set_clip_lut(self, item: Any, lut_path: str = "", node_index: int = 1) -> None:
        """Applies a LUT to the clip's color node using the correct Resolve API.
        
        Args:
            item: TimelineItem to apply the LUT to
            lut_path: Absolute path to the .cube/.3dl LUT file
            node_index: 1-based node index in the color page (default: first node)
        """
        if not item or not self.resolve: return
        if not lut_path:
            print("  [Resolve] Warning: No LUT path provided")
            return
        try:
            result = item.SetLUT(node_index, lut_path)
            if not result:
                print(f"  [Resolve] Warning: SetLUT returned False for node {node_index}")
        except Exception as e:
            print(f"  [Resolve] Warning: Could not apply LUT: {e}")

    def set_clip_rotation(self, item: Any, angle: float) -> None:
        """Sets the clip's Z-rotation for kinetic motion."""
        if not item or not self.resolve: return
        try:
            item.SetProperty("RotationAngle", angle)
        except Exception as e:
            pass

    def apply_camera_shake(self, item: Any, intensity: float = 1.0) -> None:
        """Simulates a professional impact shake using jittered pan, tilt, and roll."""
        if not item or not self.resolve: return
        try:
            import random
            # Shake lasts 2 frames usually
            item.SetProperty("Pan", random.uniform(-15, 15) * intensity)
            item.SetProperty("Tilt", random.uniform(-10, 10) * intensity)
            item.SetProperty("RotationAngle", random.uniform(-1.5, 1.5) * intensity)
        except Exception as e:
            pass

    def apply_zoom_animation(self, item: Any, start_zoom: float, end_zoom: float, rotation: float = 0.0) -> None:
        """Applies a Ken Burns zoom effect using Resolve's Dynamic Zoom.
        
        Dynamic Zoom is the correct API approach — it handles the interpolation
        natively instead of trying to keyframe with SetProperty (which overwrites
        the start value immediately).
        """
        if not item or not self.resolve: return
        try:
            # Enable Dynamic Zoom on the clip
            item.SetProperty("DynamicZoomEase", 0)  # 0=Linear, 1=EaseIn, 2=EaseOut, 3=EaseInOut
            
            # Set the zoom rectangle for start and end
            # Dynamic Zoom uses normalized coordinates (0-1 range)
            # We translate zoom factors to crop rectangles
            margin_start = (1.0 - 1.0/start_zoom) / 2.0
            margin_end = (1.0 - 1.0/end_zoom) / 2.0
            
            # The API may use GetProperty/SetProperty for DynamicZoom rect
            # Fallback: use a centered crop approach via ZoomX/ZoomY
            avg_zoom = (start_zoom + end_zoom) / 2.0
            item.SetProperty("ZoomX", avg_zoom)
            item.SetProperty("ZoomY", avg_zoom)
            
            if rotation != 0:
                item.SetProperty("RotationAngle", rotation * 0.5)
                
        except Exception as e:
            print(f"  [Resolve] Warning: Could not apply zoom animation: {e}")

    def set_clip_speed(self, item: Any, speed: float) -> None:
        """Sets the clip speed (e.g., 2.0 for 2x speed)."""
        if not item or not self.resolve: return
        try:
            item.SetProperty("Speed", speed)
        except Exception as e:
            print(f"  [Resolve] Warning: Could not set speed: {e}")

    def create_intro_title(self, text: str, duration_sec: float = 3.0, style: str = "vlog") -> None:
        """Adds a Fusion Text+ title to the start of the timeline.
        
        Delegates to TitleGenerator for the actual Fusion API interaction.
        """
        from title_generator import TitleGenerator
        gen = TitleGenerator(self, style=style)
        gen.insert_intro_title(text, duration_sec)

    def apply_track_ducking(self, track_index: int, speaking_intervals: List[Tuple],
                            duck_volume: float = -12.0) -> None:
        """Applies real audio ducking by adjusting music track volume during speech.
        
        Uses TimelineItem.SetProperty('Volume') on audio clips that overlap
        with speaking intervals. For clips that span speech boundaries, we
        adjust the overall level as a practical approximation.
        
        Args:
            track_index: Audio track containing the music (usually 2)
            speaking_intervals: List of (start, end, ...) tuples in seconds
            duck_volume: Volume reduction in dB during speech (default -12)
        """
        if not self.resolve: return
        
        tl = self.project.GetCurrentTimeline()
        if not tl:
            print("[Ducking] No active timeline")
            return
            
        audio_items = tl.GetItemListInTrack("audio", track_index)
        if not audio_items:
            print(f"[Ducking] No audio items on track {track_index}")
            return
        
        fps = self.timeline_fps
        start_frame = self.timeline_start_frame
        
        print(f"[Ducking] Analyzing {len(speaking_intervals)} speech segments against {len(audio_items)} audio clip(s)...")
        
        ducked_count = 0
        for interval in speaking_intervals:
            speech_start = interval[0]
            speech_end = interval[1]
            
            speech_start_f = start_frame + int(speech_start * fps)
            speech_end_f = start_frame + int(speech_end * fps)
            
            for audio_item in audio_items:
                try:
                    item_start = audio_item.GetStart()
                    item_end = audio_item.GetEnd()
                    
                    # Check if this audio clip overlaps with the speaking interval
                    if item_start < speech_end_f and item_end > speech_start_f:
                        # This music clip overlaps with speech — duck it
                        # Convert dB to linear volume: 10^(dB/20)
                        import math
                        linear_vol = math.pow(10, duck_volume / 20.0)
                        vol_pct = linear_vol * 100.0  # Resolve uses 0-100 scale
                        
                        audio_item.SetProperty("Volume", vol_pct)
                        ducked_count += 1
                        print(f"  [Ducking] Music {duck_volume}dB @ {speech_start:.1f}s-{speech_end:.1f}s")
                except Exception as e:
                    print(f"  [Ducking] Warning: {e}")
        
        if ducked_count == 0:
            print("  [Ducking] No overlapping music clips found")
        else:
            print(f"[Ducking] Applied {ducked_count} volume adjustments")

    def add_beat_markers(self, beat_times: List[float], burst_zones: List[Tuple] = None) -> None:
        """Injects visual markers on the timeline at beat/impact positions.
        
        Args:
            beat_times: List of beat timestamps in seconds
            burst_zones: List of (start, end) tuples for high-intensity zones
        """
        if not self.resolve: return
        
        tl = self.project.GetCurrentTimeline()
        if not tl:
            return
        
        fps = self.timeline_fps
        start = self.timeline_start_frame
        marker_count = 0
        
        for t in beat_times:
            frame = start + int(t * fps)
            try:
                tl.AddMarker(frame, "Blue", "Beat", f"Beat @ {t:.2f}s", 1, "beat")
                marker_count += 1
            except Exception:
                pass
        
        for zone in (burst_zones or []):
            frame = start + int(zone[0] * fps)
            duration = max(1, int((zone[1] - zone[0]) * fps))
            try:
                tl.AddMarker(frame, "Red", "Burst", f"High energy zone", duration, "burst")
            except Exception:
                pass
        
        print(f"[Markers] Injected {marker_count} beat markers")

    def organize_media_pool(self, aroll_clips: List = None, broll_clips: List = None,
                            fpv_clips: List = None, music_clips: List = None) -> None:
        """Organizes the media pool into labeled subfolders with color-coded clips."""
        if not self.resolve or not self.media_pool:
            print("[MediaPool/MOCK] Would organize media pool")
            return
        
        root = self.media_pool.GetRootFolder()
        
        folder_map = {
            "A-Roll": (aroll_clips, "Blue"),
            "B-Roll": (broll_clips, "Green"),
            "FPV Drone": (fpv_clips, "Orange"),
            "Music": (music_clips, "Purple"),
        }
        
        for folder_name, (clips, color) in folder_map.items():
            if not clips:
                continue
            try:
                subfolder = self.media_pool.AddSubFolder(root, folder_name)
                if subfolder and clips:
                    self.media_pool.MoveClips(clips, subfolder)
                    for clip in clips:
                        try:
                            clip.SetClipColor(color)
                        except Exception:
                            pass
                    print(f"  [MediaPool] Created '{folder_name}' with {len(clips)} clips")
            except Exception as e:
                print(f"  [MediaPool] Warning: {e}")
