import os
import urllib.parse

class XMLGeneratorV2:
    def __init__(self, timeline_name, fps=24.0):
        self.timeline_name = timeline_name
        self.fps = fps
        self.assets = []
        self.clips = []
        self.asset_counter = 1

    def add_asset(self, file_path, duration_sec, uid=None):
        # Resolve-native path formatting for Windows
        # Standard: file:///C:/Path/To/File
        norm_path = file_path.replace('\\', '/')
        if norm_path.startswith('/'):
            norm_path = norm_path[1:] # Remove leading slash if it exists
        
        # URI encoding but keeping the colon and slashes intact
        drive, rest = os.path.splitdrive(norm_path)
        encoded_rest = urllib.parse.quote(rest)
        uri = f"file:///{drive}{encoded_rest}"
        
        asset_id = f"r{self.asset_counter}"
        self.asset_counter += 1
        
        duration_frames = int(duration_sec * self.fps)
        
        self.assets.append({
            "id": asset_id,
            "uid": uid if uid else asset_id,
            "name": os.path.basename(file_path),
            "src": uri,
            "duration": f"{duration_frames}/{int(self.fps)}s"
        })
        return asset_id

    def add_clip(self, asset_id, name, start_sec, duration_sec, offset_sec):
        start_f = int(start_sec * self.fps)
        dur_f = int(duration_sec * self.fps)
        offset_f = int(offset_sec * self.fps)
        
        self.clips.append({
            "asset_id": asset_id,
            "name": name,
            "start": f"{start_f}/{int(self.fps)}s",
            "duration": f"{dur_f}/{int(self.fps)}s",
            "offset": f"{offset_f}/{int(self.fps)}s",
            "has_transition": False
        })

    def add_transition(self, duration_sec=0.5):
        if self.clips:
            self.clips[-1]["has_transition"] = True
            self.clips[-1]["transition_duration"] = int(duration_sec * self.fps)

    def generate(self, output_path):
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<!DOCTYPE fcpxml>\n'
        xml += '<fcpxml version="1.8">\n'
        xml += '  <resources>\n'
        xml += '    <format id="r0" name="FFVideoFormat1080p24" frameDuration="1/24s" width="1920" height="1080"/>\n'
        
        for asset in self.assets:
            # Injecting uid for direct Resolve handshake
            xml += f'    <asset id="{asset["id"]}" name="{asset["name"]}" src="{asset["src"]}" duration="{asset["duration"]}" uid="{asset["uid"]}" hasVideo="1" hasAudio="1"/>\n'
        
        xml += '  </resources>\n'
        xml += '  <library>\n'
        xml += f'    <event name="{self.timeline_name}">\n'
        xml += f'      <project name="{self.timeline_name}">\n'
        xml += f'        <sequence format="r0" duration="3600/24s" tcStart="0s" tcFormat="NDF">\n'
        xml += '          <spine>\n'
        
        for i, clip in enumerate(self.clips):
            xml += f'            <video name="{clip["name"]}" offset="{clip["offset"]}" ref="{clip["asset_id"]}" duration="{clip["duration"]}" start="{clip["start"]}">\n'
            if clip["has_transition"] and i < len(self.clips) - 1:
                t_dur = clip["transition_duration"]
                xml += f'              <transition name="Cross Dissolve" offset="{clip["duration"]}" duration="{t_dur}/24s"/>\n'
            xml += '            </video>\n'

        xml += '          </spine>\n'
        xml += '        </sequence>\n'
        xml += '      </project>\n'
        xml += '    </event>\n'
        xml += '  </library>\n'
        xml += '</fcpxml>\n'
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[XML] Emergency Fixed V9.2 XML generated: {output_path}")
