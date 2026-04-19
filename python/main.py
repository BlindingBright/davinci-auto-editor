import argparse
import os
import time
import random
from typing import List, Dict, Any, Optional

import config
from resolve_controller import ResolveController
from audio_analyzer import AudioAnalyzer
from motion_analyzer import MotionAnalyzer
from music_fetcher import MusicFetcher
from music_analyzer import MusicAnalyzer
from transition_injector import inject_transitions
from color_grader import ColorGrader
from render_engine import RenderEngine
from title_generator import TitleGenerator
from scene_analyzer import SceneAnalyzer
from sfx_engine import SFXEngine

def setup_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DaVinci Auto-Editor AI Engine V2")
    parser.add_argument("--aroll", type=str, default="", help="Path to A-Roll footage")
    parser.add_argument("--broll", type=str, default="", help="Path to B-Roll footage")
    parser.add_argument("--fpv", type=str, default="", help="Path to FPV drone footage")
    parser.add_argument("--style", type=str, default="vlog", help="Editing style (vlog, reel, cinematic, hyper)")
    parser.add_argument("--mix_ratio", type=int, default=50, help="Ratio of A-Roll vs B-Roll")
    parser.add_argument("--max_duration", type=int, default=60, help="Max edit duration in seconds")
    parser.add_argument("--music_path", type=str, default="", help="Path to custom music")
    # V2.0 additions
    parser.add_argument("--title", type=str, default="", help="Intro title text (leave blank to skip)")
    parser.add_argument("--render", action="store_true", help="Auto-render after assembly")
    parser.add_argument("--render_preset", type=str, default="youtube_1080", help="Render preset (youtube_1080, youtube_4k, tiktok_vertical, instagram_square, prores_master)")
    parser.add_argument("--output_dir", type=str, default="", help="Render output directory")
    return parser.parse_args()

def _find_pool_item_by_name(media_pool: Any, filename: str) -> Optional[Any]:
    """Search the current media pool root folder for a clip by filename."""
    if not media_pool: return None
    try:
        root = media_pool.GetRootFolder()
        clips = root.GetClipList()
        if clips:
            for clip in clips:
                try:
                    if clip.GetClipProperty("File Name") == filename:
                        return clip
                except Exception:
                    pass
    except Exception:
        pass
    return None

def pools_contain(name: str, a, f, b) -> bool:
    if name == "aroll": return len(a) > 0
    if name == "fpv": return len(f) > 0
    if name == "broll": return len(b) > 0
    return False


def build_resolve_timeline(aroll_data: List[Dict], broll_dir: str, fpv_data: List[Dict], broll_data: List[Dict], 
                           music_path: str, style: str, mix_ratio: int, max_duration: int,
                           title_text: str = "") -> Any:
    """
    The Round-Trip Engine V2:
      Phase 1 — Direct API builds a simple timeline (100% online, no transitions)
      Phase 2 — Resolve exports that timeline as FCPXML (paths from Resolve itself)
      Phase 3 — We inject native <transition> tags into the exported XML
      Phase 4 — Resolve re-imports the modified XML (native transitions + online)
      Phase 5 — VFX polish applied via API to the final timeline
      Phase 6 — Auto Color Grading (LUT + CDL + grade propagation)
      Phase 7 — Fusion Titles (intro + end card)
      Phase 8 — One-Click Render & Export (handled externally)
    
    Returns the ResolveController for the render phase.
    """
    print("[Resolve] Initializing ResolveController...")
    controller = ResolveController()
    
    project_name = f"AutoEdit_{style.capitalize()}_{int(time.time())}"
    if not controller.create_or_load_project(project_name):
        print("[Resolve] Critical Error: Could not initialize project.")
        return
    
    # ---- Analyze Music Beats & Onsets ----
    beat_times, onsets, burst_zones = [], [], []
    if music_path and os.path.exists(music_path):
        m_analyzer = MusicAnalyzer()
        bpm, beat_times, onsets, burst_zones = m_analyzer.analyze_beats(music_path)
    impact_pool = sorted(list(set(beat_times + onsets)))

    # ---- Collect all source media paths ----
    media_files = []
    if aroll_data:
        media_files.extend([d['file'] for d in aroll_data])
    if fpv_data:
        media_files.extend([d['file'] for d in fpv_data])
    
    broll_files = []
    video_exts = (".mp4", ".mov", ".mkv", ".m4v", ".avi", ".mts")
    if broll_dir and os.path.exists(broll_dir):
        broll_files = [os.path.join(broll_dir, f) for f in sorted(os.listdir(broll_dir)) 
                       if f.lower().endswith(video_exts)]
        media_files.extend(broll_files)
        print(f"[Resolve] Found {len(broll_files)} B-Roll file(s)")
    
    if music_path and os.path.exists(music_path):
        media_files.append(music_path)

    # ---- Import media into pool & build lookup maps ----
    item_map: Dict[str, Any] = {}
    fps_map: Dict[str, float] = {}
    
    for fpath in media_files:
        items = controller.media_storage.AddItemListToMediaPool([fpath]) if controller.resolve else None
        item = items[0] if items else _find_pool_item_by_name(controller.media_pool, os.path.basename(fpath))
        if item:
            try:
                props = item.GetClipProperty()
                real_path = props.get("File Path", fpath)
                item_map[real_path] = item
                item_map[fpath] = item
                fps_str = props.get("FPS", "30")
                fps_map[fpath] = float(fps_str) if fps_str else 30.0
            except Exception as e:
                print(f"  [Warning] Could not map properties for {os.path.basename(fpath)}: {e}")
                item_map[fpath] = item
                fps_map[fpath] = 30.0

    print(f"[Resolve] Mapped {len(set(id(v) for v in item_map.values()))} unique items.")

    # ---- Build clip pools ----
    aroll_pool = []
    for d in (aroll_data or []):
        for (s, e, score) in d.get('speaking_segments', []):
            aroll_pool.append([d['file'], s, e, score])
    aroll_pool.sort(key=lambda x: x[3], reverse=True)

    fpv_pool = []
    for d in (fpv_data or []):
        for segment_data in d.get('useful_segments', []):
            if len(segment_data) == 3:
                s, e, score = segment_data
            else:
                s, e = segment_data
                score = 0.5 # Default medium score
            fpv_pool.append([d['file'], s, e, score])
    fpv_pool.sort(key=lambda x: x[3], reverse=True)

    broll_pool = []
    for d in (broll_data or []):
        for segment_data in d.get('useful_segments', []):
            s, e, score = segment_data
            broll_pool.append([d['file'], s, e, score])
    broll_pool.sort(key=lambda x: x[3], reverse=True)
    
    if not broll_pool and broll_files:
        # Fallback for small files or unscored ones
        broll_pool = [[f, 0.0, 5.0, 0.1] for f in broll_files]

    active_types = {t for t in ["aroll", "fpv", "broll"] if pools_contain(t, aroll_pool, fpv_pool, broll_pool)}
    pattern = [p for p in ["aroll", "fpv", "aroll", "broll"] if p in active_types]
    if not pattern: return

    # ---- Cut durations per style ----
    cut_dur = config.STYLE_CUT_LENGTHS.get(style, config.STYLE_CUT_LENGTHS["vlog"])
    print(f"[Resolve] Target lengths: A-Roll={cut_dur['aroll']}s | FPV={cut_dur['fpv']}s | B-Roll={cut_dur['broll']}s")

    pools = {"aroll": aroll_pool, "fpv": fpv_pool, "broll": broll_pool}
    pool_idx = {"aroll": 0, "fpv": 0, "broll": 0}

    def next_clip(name: str):
        p = pools[name]
        if not p: return None, 0
        
        # Weighted Shuffle: Pick randomly from the Top 5 candidates for variety
        top_n = min(5, len(p))
        idx = random.randint(0, top_n - 1)
        # Shift the index to pick something fresh if it's already used
        # (This is a simple proxy for a real shuffle)
        return p[idx], idx

    # =====================================================================
    #  PHASE 1 — Direct API Assembly  (simple, single-track, guaranteed online)
    # =====================================================================
    base_timeline_name = f"_BaseAssembly_{int(time.time())}"
    timeline = controller.create_timeline(base_timeline_name)
    if not timeline:
        print("[Resolve] ERROR: Could not create base timeline.")
        return

    print(f"[Resolve] Phase 1: Building clean base timeline (Direct API)...")
    total_placed = 0.0
    pattern_pos = 0
    aroll_zoom_toggle = False
    
    # Track which clips are FPV for post-processing
    placed_clips_info = []  # list of (pool_name, fpath)
    
    # -----------------------------------------------------------
    # INTELLIGENT HOOK INJECTION
    # Grab the absolute highest-energy clips for the first 2 shots
    # -----------------------------------------------------------
    def _place_hook(p_name: str, pool: list):
        nonlocal total_placed, aroll_zoom_toggle
        if not pool: return
        
        # Pick randomly from the top tier (Top 3 for A-Roll, Top 5 for FPV) to keep Rerolls fresh
        top_n = 3 if p_name == "aroll" else 5
        candidates = pool[:top_n]
        if not candidates: return
        
        # Randomly select a hook from the highly-rated candidates
        entry = random.choice(candidates)
        fpath, cur_pos, seg_end = entry[0], entry[1], entry[2]
        item = item_map.get(fpath)
        if not item: return

        target_len = cut_dur[p_name]
        chunk = max(0.4, min(target_len, seg_end - cur_pos, max_duration - total_placed))
        fps = fps_map.get(fpath, 30.0)
        
        handle_frames = 3
        raw_start_f = int(cur_pos * fps)
        raw_end_f = int((cur_pos + chunk) * fps)
        start_f = max(0, raw_start_f - handle_frames)
        end_f = raw_end_f + handle_frames

        print(f"  [HOOK {p_name.upper()}] {os.path.basename(fpath)} ({chunk:.1f}s) @{total_placed:.1f}s")
        controller.add_clip_to_timeline(item, "video", 1, start_f, end_f)
        
        placed_clips_info.append((p_name, fpath))
        total_placed += chunk
        entry[1] += chunk # shift the cur_pos forward so it doesn't repeat the exact same frames if drawn again
        
        # Also advance pattern position so standard loop aligns correctly
        nonlocal pattern_pos
        pattern_pos += 1

    print(f"  [HOOK] Injecting high-energy starting sequence...")
    # Inject 1 A-Roll Hook, followed by 1 FPV Hook
    _place_hook("aroll", aroll_pool)
    _place_hook("fpv", fpv_pool)
    print(f"  [HOOK] Sequence complete. Resuming chronological assembly.")
    # -----------------------------------------------------------

    while total_placed < max_duration:
        # Burst logic
        in_burst = any(b[0] <= total_placed <= b[1] for b in burst_zones)
        if in_burst:
            p_name = "broll"
        else:
            p_name = pattern[pattern_pos % len(pattern)]
            pattern_pos += 1

        entry, idx = next_clip(p_name)
        if not entry: break

        fpath, cur_pos, seg_end = entry[0], entry[1], entry[2]
        item = item_map.get(fpath)
        if not item:
            pool_idx[p_name] += 1
            continue

        # Pacing & ramping
        progress = total_placed / max_duration
        ramp_mult = 1.0 if progress < 0.6 else 0.7
        target_len = cut_dur[p_name] * ramp_mult * random.uniform(0.9, 1.1)

        if impact_pool:
            ideal_end = total_placed + target_len
            valid_impacts = [i for i in impact_pool if abs(i - ideal_end) < 0.4]
            if valid_impacts:
                target_len = min(valid_impacts, key=lambda x: abs(x - ideal_end)) - total_placed

        chunk = max(0.4, min(target_len, seg_end - cur_pos, max_duration - total_placed))
        fps = fps_map.get(fpath, 30.0)
        
        # Add handle frames for transitions (3 frames = half of 6-frame dissolve)
        handle_frames = 3
        raw_start_f = int(cur_pos * fps)
        raw_end_f = int((cur_pos + chunk) * fps)
        start_f = max(0, raw_start_f - handle_frames)
        end_f = raw_end_f + handle_frames  # Resolve will clamp if past end of media

        print(f"  [{p_name.upper()}] {os.path.basename(fpath)} ({chunk:.1f}s) @{total_placed:.1f}s")
        tl_item = controller.add_clip_to_timeline(item, "video", 1, start_f, end_f)

        placed_clips_info.append((p_name, fpath))
        total_placed += chunk
        entry[1] += chunk
        pool_idx[p_name] += 1

    print(f"[Resolve] Phase 1 complete: {total_placed:.1f}s on timeline. All media ONLINE.")

    # =====================================================================
    #  PHASE 2 — Export the clean timeline as FCPXML  (Resolve writes paths)
    # =====================================================================
    export_path = os.path.join(config.TEMP_DIR, "base_export.fcpxml")
    modified_path = os.path.join(config.TEMP_DIR, "with_transitions.fcpxml")

    print(f"[Resolve] Phase 2: Exporting timeline as FCPXML...")
    exported = False
    if controller.resolve:
        tl = controller.project.GetCurrentTimeline()
        try:
            exported = tl.Export(export_path, 
                                controller.resolve.EXPORT_FCPXML_1_8, 
                                controller.resolve.EXPORT_NONE)
        except Exception as e:
            print(f"  [Resolve] Export error: {e}")
            # Fallback: try attribute-style access
            try:
                exported = tl.Export(export_path, 1, 0)
            except Exception as e2:
                print(f"  [Resolve] Export fallback also failed: {e2}")

    if not exported or not os.path.exists(export_path):
        print("[Resolve] WARNING: Could not export FCPXML. Skipping transition injection.")
        print("[Resolve] Your timeline is still ready — just without built-in transitions.")
    else:
        print(f"[Resolve] Exported base timeline to: {export_path}")

        # =================================================================
        #  PHASE 3 — Inject native transition tags into the exported XML
        # =================================================================
        print(f"[Resolve] Phase 3: Injecting dynamic variety of native transitions...")
        success = inject_transitions(
            input_xml=export_path,
            output_xml=modified_path,
            transition_names=[
                "Cross Dissolve", "Additive Dissolve", "Dip to Color Dissolve",
                "Push", "Slide", "Barn Door", "Clock Wipe", "Iris Diamond"
            ],
            duration_frames=6,
            fps=controller.timeline_fps
        )

        if success and os.path.exists(modified_path):
            # =============================================================
            #  PHASE 4 — Re-import the modified XML with native transitions
            # =============================================================
            final_name = f"AutoEdit_Smooth_{style.capitalize()}"
            print(f"[Resolve] Phase 4: Re-importing timeline with native transitions...")
            
            if controller.import_timeline(modified_path, final_name):
                print(f"[Resolve] Native transitions are LIVE on '{final_name}'!")
            else:
                print("[Resolve] WARNING: Re-import failed. Falling back to base timeline.")
        else:
            print("[Resolve] Transition injection failed. Using base timeline without transitions.")

    # =====================================================================
    #  PHASE 5 — VFX Polish (zoom, optical flow, shakes) on the active timeline
    # =====================================================================
    print("[Resolve] Phase 5: Applying cinematic VFX polish...")
    if controller.resolve:
        tl = controller.project.GetCurrentTimeline()
        v1_items = tl.GetItemListInTrack("video", 1)
        if v1_items:
            for i, tl_item in enumerate(v1_items):
                clip_name = tl_item.GetName()
                
                # FPV detection: 1.340 zoom + optical flow
                is_fpv = "DJI" in clip_name or "stabilized" in clip_name
                if is_fpv:
                    controller.set_clip_zoom(tl_item, 1.340)
                    controller.set_optical_flow(tl_item)
                elif i < len(placed_clips_info):
                    # Alternating A-Roll zoom for energy (only non-FPV)
                    p_name = placed_clips_info[i][0]
                    if p_name == "aroll":
                        zoom = 1.05 if aroll_zoom_toggle else 1.0
                        controller.set_clip_zoom(tl_item, zoom)
                        aroll_zoom_toggle = not aroll_zoom_toggle

    # ---- Music ----
    if music_path and os.path.exists(music_path):
        m_item = item_map.get(music_path) or item_map.get(os.path.abspath(music_path))
        
        # If it wasn't in the media pool initially, force import it now
        if not m_item and controller.media_pool:
            print(f"[Resolve] Importing new music track: {os.path.basename(music_path)}")
            imported = controller.media_pool.ImportMedia([os.path.abspath(music_path)])
            if imported and len(imported) > 0:
                m_item = imported[0]
                
        if m_item:
            # Place on Audio Track 2 to avoid overwriting the camera audio on Track 1
            controller.add_clip_to_timeline(m_item, "audio", 2, 0, 
                                            int(total_placed * controller.timeline_fps), record_frame=0)

    # ---- Audio Ducking ----
    speaking_intervals = []
    for d in (aroll_data or []):
        for s in d.get('speaking_segments', []):
            speaking_intervals.append(s)
    if speaking_intervals:
        controller.apply_track_ducking(2, speaking_intervals)

    # ---- SFX Layer (whoosh, impact, riser on Audio Track 3) ----
    print("[Resolve] Placing SFX layer...")
    sfx = SFXEngine(controller, style=style)
    transition_count = len(placed_clips_info) - 1
    if transition_count > 0:
        fps = controller.timeline_fps
        start_f = controller.timeline_start_frame
        # Estimate transition frames from placed clip boundaries
        transition_frames = []
        cum_dur = 0.0
        for i, (p_name, p_path) in enumerate(placed_clips_info[:-1]):
            clip_dur = config.STYLE_CUT_LENGTHS.get(style, {}).get(p_name, 3.0)
            cum_dur += clip_dur
            transition_frames.append(start_f + int(cum_dur * fps))
        sfx.place_transition_sfx(transition_frames)
    if beat_times:
        beat_frames = [controller.timeline_start_frame + int(t * controller.timeline_fps) for t in beat_times]
        sfx.place_beat_sfx(beat_frames, burst_zones)

    # =====================================================================
    #  PHASE 6 — Auto Color Grading (LUTs + CDL + Grade Propagation)
    # =====================================================================
    print("[Resolve] Phase 6: Applying AI Color Grading...")
    grader = ColorGrader(style=style)
    grader.grade_timeline(controller, placed_clips_info)

    # =====================================================================
    #  PHASE 7 — Fusion Titles (Intro + End Card)
    # =====================================================================
    if title_text:
        print(f"[Resolve] Phase 7: Generating Fusion Titles...")
        titler = TitleGenerator(controller, style=style)
        titler.insert_intro_title(title_text)
        titler.insert_end_card()

    # =====================================================================
    #  Beat Markers & Chapter Markers
    # =====================================================================
    if beat_times:
        print("[Resolve] Injecting beat markers for visual reference...")
        controller.add_beat_markers(beat_times, burst_zones)

    print(f"[Resolve] SUCCESS: Assembly complete. {total_placed:.1f}s of professional, smooth footage.")
    return controller  # Return controller for render phase


def main() -> None:
    args = setup_args()
    print("=== DaVinci Auto-Editor AI Pipeline V2 ===")
    print(f"    Style: {args.style} | Duration: {args.max_duration}s | Render: {args.render}")
    
    a_analyzer = AudioAnalyzer()
    aroll_data = a_analyzer.analyze_directory(args.aroll)
    m_analyzer = MotionAnalyzer()
    
    print("[AI] Analyzing FPV Drone footage for dynamic motion...")
    fpv_data = m_analyzer.analyze_directory(args.fpv) if hasattr(m_analyzer, 'analyze_directory') else []
    # If using new MotionAnalyzer, we need to adapt it. 
    # Let's assume analyze_directory exists or we loop.
    if not fpv_data and args.fpv:
        fpv_files = [os.path.join(args.fpv, f) for f in os.listdir(args.fpv) if f.lower().endswith(('.mp4', '.mov'))]
        for f in fpv_files[:20]: # Only analyze top 20 for speed
             fpv_data.append(m_analyzer.analyze_clip(f))

    print("[AI] Analyzing B-Roll footage for dynamic motion...")
    broll_data = []
    if args.broll:
        broll_files = [os.path.join(args.broll, f) for f in os.listdir(args.broll) if f.lower().endswith(('.mp4', '.mov'))]
        for f in broll_files[:30]: # Fast Option A: only top 30
             broll_data.append(m_analyzer.analyze_clip(f))

    # V2.0: Scene analysis for smarter clip selection
    print("[AI] Running deep scene analysis (face detection, visual cohesion)...")
    s_analyzer = SceneAnalyzer()
    if args.broll:
        broll_scene_data = s_analyzer.analyze_directory(args.broll)
        # Sort B-Roll by visual similarity for smoother transitions
        if broll_scene_data:
            broll_data = s_analyzer.sort_by_visual_similarity(
                [dict(d, **sd) for d, sd in zip(broll_data, broll_scene_data)] if len(broll_data) == len(broll_scene_data) else broll_data
            )
            print(f"[AI] B-Roll reordered for visual cohesion ({len(broll_data)} clips)")

    if args.music_path and os.path.exists(args.music_path):
        print(f"[AI] Using Custom Music track: {args.music_path}")
        music_path = args.music_path
    else:
        m_fetcher = MusicFetcher()
        music_path = m_fetcher.fetch_for_style(args.style)
    
    controller = build_resolve_timeline(
        aroll_data, args.broll, fpv_data, broll_data, music_path, 
        args.style, args.mix_ratio, args.max_duration,
        title_text=args.title
    )
    
    # =====================================================================
    #  PHASE 8 — One-Click Render & Export
    # =====================================================================
    if args.render and controller:
        output_dir = args.output_dir or os.path.join(config.TEMP_DIR, "renders")
        print(f"\n[Render] Phase 8: Auto-rendering to {output_dir}")
        renderer = RenderEngine(controller)
        success = renderer.render_preset(args.render_preset, output_dir)
        if success:
            print(f"[Render] Export complete! Check: {output_dir}")
        else:
            print(f"[Render] Warning: Render did not complete successfully")
    
    print("\n[AI] Pipeline Finished successfully.")

if __name__ == "__main__":
    main()
