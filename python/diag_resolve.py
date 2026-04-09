import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Connect to Resolve
resolve_path = os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                            "Blackmagic Design", "DaVinci Resolve", "Support",
                            "Developer", "Scripting", "Modules")
if resolve_path not in sys.path:
    sys.path.append(resolve_path)

import DaVinciResolveScript as dvr
resolve = dvr.scriptapp("Resolve")
pm = resolve.GetProjectManager()
ms = resolve.GetMediaStorage()

print("=== Resolve API Diagnostic ===")
print(f"Resolve: {resolve}")
print(f"ProjectManager: {pm}")

# Create fresh project
proj_name = "DIAG_TEST_001"
proj = pm.LoadProject(proj_name)
if not proj:
    proj = pm.CreateProject(proj_name)
print(f"Project: {proj}")

pool = proj.GetMediaPool()
print(f"MediaPool: {pool}")

# Test adding a real file
test_file = r"E:\Zoe\SKE Ent\Video\Drone Footage\DJI_20260301025250_0002_D_stabilized_1.mp4"
print(f"\nAdding file: {os.path.basename(test_file)}")
items = ms.AddItemListToMediaPool([test_file])
print(f"Result from AddItemListToMediaPool: {items}")
print(f"Type: {type(items)}")
if items:
    item = items[0]
    print(f"Item: {item}")
    print(f"Item type: {type(item)}")
    try:
        props = item.GetClipProperty()
        print(f"All props keys: {list(props.keys())[:10]}")
        print(f"File Name: {props.get('File Name', 'N/A')}")
        print(f"File Path: {props.get('File Path', 'N/A')}")
        print(f"Duration: {props.get('Duration', 'N/A')}")
        print(f"FPS: {props.get('FPS', 'N/A')}")
        end_frame = props.get('End Frame', props.get('Frames', 100))
        print(f"End Frame: {end_frame}")
    except Exception as e:
        print(f"GetClipProperty error: {e}")

# Create timeline and try to append clip
print("\nCreating timeline...")
timeline = pool.CreateEmptyTimeline("DIAG_TL_001")
print(f"Timeline: {timeline}")

if timeline and items:
    print("\nAttempting AppendToTimeline...")
    clip_info = {
        "mediaPoolItem": items[0],
        "startFrame": 0,
        "endFrame": 900,
        "trackIndex": 1,
        "recordFrame": 0,
    }
    result = pool.AppendToTimeline([clip_info])
    print(f"AppendToTimeline result: {result}")

    # Also try simple append with no clip_info
    print("\nAttempting simple AppendToTimeline (no clip_info)...")
    result2 = pool.AppendToTimeline([items[0]])
    print(f"Simple append result: {result2}")
