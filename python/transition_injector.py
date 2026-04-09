"""
Transition Injector — The Round-Trip Engine (V2)

Reads an FCPXML exported by Resolve and injects native transition elements.
Supports cycling through multiple transition types for variety.
"""
import xml.etree.ElementTree as ET
from fractions import Fraction
from typing import List, Union


def _parse_time(time_str: str) -> Fraction:
    """Parse FCPXML time string like '86425/24s' or '3600/1s' into a Fraction."""
    if not time_str:
        return Fraction(0)
    time_str = time_str.rstrip('s')
    if '/' in time_str:
        parts = time_str.split('/')
        return Fraction(int(parts[0]), int(parts[1]))
    return Fraction(int(time_str))


def _format_time(frac: Fraction) -> str:
    """Format a Fraction back to FCPXML time string like '86425/24s'."""
    if frac.denominator == 1:
        return f"{frac.numerator}/1s"
    return f"{frac.numerator}/{frac.denominator}s"


def inject_transitions(input_xml: str, output_xml: str,
                       transition_names: Union[str, List[str]] = "Cross Dissolve",
                       duration_frames: int = 6, fps: float = 24.0) -> bool:
    """
    Reads an FCPXML exported by Resolve and injects native transitions.
    
    Args:
        transition_names: A single name or list of names to cycle through.
        duration_frames: Total transition length in frames (default 6 = 0.25s).
    """
    # Normalize to list
    if isinstance(transition_names, str):
        transition_names = [transition_names]
    
    try:
        tree = ET.parse(input_xml)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"[TransitionInjector] XML parse error: {e}")
        return False

    spine = root.find(".//spine")
    if spine is None:
        print("[TransitionInjector] ERROR: No <spine> element found.")
        return False

    clips = list(spine)
    if len(clips) < 2:
        print("[TransitionInjector] Only 0-1 clips — nothing to transition.")
        return False

    # Transition duration as a fraction of seconds
    trans_dur = Fraction(duration_frames, int(fps))

    # Build new spine content with transitions inserted between clips.
    new_elements = []

    for i, clip in enumerate(clips):
        if i == 0:
            # First clip — no adjustment needed
            new_elements.append(clip)
        else:
            # Pick transition type by cycling through the list
            t_name = transition_names[i % len(transition_names)]
            
            # Insert a transition element before this clip
            trans = ET.Element("transition")
            trans.set("name", t_name)
            trans.set("duration", _format_time(trans_dur))
            
            # Shift this clip's offset earlier by the transition duration
            clip_offset = _parse_time(clip.get("offset", "0/1s"))
            new_offset = clip_offset - trans_dur
            clip.set("offset", _format_time(new_offset))
            trans.set("offset", _format_time(new_offset))
            
            new_elements.append(trans)
            new_elements.append(clip)

    # Adjust sequence duration for overlaps
    sequence = root.find(".//sequence")
    if sequence is not None:
        orig_dur = _parse_time(sequence.get("duration", "0/1s"))
        overlap_total = trans_dur * (len(clips) - 1)
        new_dur = orig_dur - overlap_total
        if new_dur > 0:
            sequence.set("duration", _format_time(new_dur))

    # Rebuild spine
    spine_attribs = dict(spine.attrib)
    spine.clear()
    for k, v in spine_attribs.items():
        spine.set(k, v)
    for elem in new_elements:
        spine.append(elem)

    tree.write(output_xml, encoding="UTF-8", xml_declaration=True)
    
    n_transitions = len(clips) - 1
    types_used = set(transition_names)
    print(f"[TransitionInjector] Injected {n_transitions} transitions ({', '.join(types_used)})")
    print(f"[TransitionInjector] Duration: {duration_frames} frames ({float(trans_dur):.3f}s)")
    print(f"[TransitionInjector] Output: {output_xml}")
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python transition_injector.py <input.fcpxml> <output.fcpxml>")
        sys.exit(1)
    inject_transitions(sys.argv[1], sys.argv[2])
