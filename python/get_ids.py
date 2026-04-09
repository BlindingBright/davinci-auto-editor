import sys
sys.path.append('C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules')
import DaVinciResolveScript as dvr

def get_mappings():
    resolve = dvr.scriptapp('Resolve')
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    mp = project.GetMediaPool()
    
    clips = mp.GetRootFolder().GetClipList()
    for clip in clips:
        path = clip.GetClipProperty("File Path")
        uid = clip.GetUniqueId()
        if path:
            print(f"{path}|{uid}")

if __name__ == "__main__":
    get_mappings()
