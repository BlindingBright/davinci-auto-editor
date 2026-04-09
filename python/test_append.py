import os
import sys

# Add Resolve scripting path
sys.path.append(os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), 
                           "Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Modules"))

try:
    import DaVinciResolveScript as dvr
except ImportError:
    print("Could not find DaVinciResolveScript")
    sys.exit(1)

resolve = dvr.scriptapp("Resolve")
if not resolve:
    print("Resolve not running")
    sys.exit(1)

project_manager = resolve.GetProjectManager()
project = project_manager.GetCurrentProject()
if not project:
    print("No project open. Please open a project first.")
    sys.exit(1)

media_pool = project.GetMediaPool()
root_folder = media_pool.GetRootFolder()
clips = root_folder.GetClipList()

if not clips:
    print("No clips in Media Pool. Please add a clip first.")
    sys.exit(1)

# Pick a test clip
test_clip = clips[0]
print(f"Testing with clip: {test_clip.GetName()}")
props = test_clip.GetClipProperty()
print(f"Clip Properties: {props}")

start_frame = int(props.get("Start", 0))
end_frame = start_frame + 50
print(f"Using absolute frames: {start_frame} to {end_frame}")

# Create a test timeline
timeline_name = "API_Test_Timeline"
timeline = None
count = project.GetTimelineCount()
for i in range(1, count + 1):
    t = project.GetTimelineByIndex(i)
    if t.GetName() == timeline_name:
        timeline = t
        break

if not timeline:
    timeline = media_pool.CreateEmptyTimeline(timeline_name)

if not timeline:
    print("Failed to create/find timeline")
    sys.exit(1)

project.SetCurrentTimeline(timeline)

# Get Timeline Start Frame & FPS
tl_start = int(timeline.GetStartFrame())
tl_fps = float(timeline.GetSetting("timelineFrameRate"))
print(f"Timeline: starts at frame {tl_start}, FPS: {tl_fps}")

# Test Gapless Append (Omitting recordFrame)
clip_info_no_rec1 = {
    "mediaPoolItem": test_clip,
    "startFrame": start_frame,
    "endFrame": start_frame + 24,
    "trackIndex": 1
}

clip_info_no_rec2 = {
    "mediaPoolItem": test_clip,
    "startFrame": start_frame + 24,
    "endFrame": start_frame + 48,
    "trackIndex": 1
}

success = media_pool.AppendToTimeline([clip_info_no_rec1, clip_info_no_rec2])
print(f"Gapless Append result: {success}")

if success:
    print("Clip appended! Check your Resolve timeline.")
else:
    print("AppendToTimeline failed.")
