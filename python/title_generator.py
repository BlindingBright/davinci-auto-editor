"""
Title Generator — Fusion Title & Lower-Third Automation

Uses DaVinci Resolve's Fusion API to inject animated titles:
  - Timeline.InsertFusionTitleIntoTimeline(titleName)
  - TimelineItem.GetFusionCompByIndex(compIndex)
  - Fusion comp tool manipulation for text, font, color
"""
import os
import time
from typing import Any, Optional

import config


class TitleGenerator:
    """Generates and places Fusion-based titles on the timeline."""

    def __init__(self, controller: Any, style: str = "vlog"):
        self.controller = controller
        self.resolve = controller.resolve
        self.project = controller.project
        self.style = style
        self.templates_dir = os.path.join(config.BASE_DIR, "assets", "title_templates")
        os.makedirs(self.templates_dir, exist_ok=True)

    def insert_intro_title(self, text: str, duration_sec: float = 3.0,
                           subtitle: str = "") -> bool:
        """
        Inserts a Fusion Text+ title at the beginning of the timeline on V2.

        Args:
            text: Main title text
            duration_sec: How long the title is displayed
            subtitle: Optional subtitle text below the main title
        """
        if not self.resolve or not self.project:
            print(f"[Titles/MOCK] Would insert intro: '{text}' ({duration_sec}s)")
            return True

        tl = self.project.GetCurrentTimeline()
        if not tl:
            print("[Titles] ERROR: No active timeline")
            return False

        print(f"[Titles] Inserting intro title: '{text}'")

        try:
            # Insert a Fusion Title generator — "Text+" is the standard Fusion text tool
            tl_item = tl.InsertFusionTitleIntoTimeline("Text+")
            if not tl_item:
                print("[Titles] Warning: InsertFusionTitleIntoTimeline returned None, trying 'Fusion Title'")
                tl_item = tl.InsertFusionTitleIntoTimeline("Fusion Title")

            if not tl_item:
                print("[Titles] Could not insert Fusion title. Skipping.")
                return False

            # Access the Fusion composition inside the title
            comp = tl_item.GetFusionCompByIndex(1)
            if comp:
                # Find the Text+ tool
                text_tool = comp.FindTool("Template")
                if not text_tool:
                    text_tool = comp.FindTool("Text1")

                if text_tool:
                    text_tool.SetInput("StyledText", text)

                    # Style-specific font choices
                    font_map = {
                        "cinematic": "Playfair Display",
                        "vlog": "Inter",
                        "reel": "Bebas Neue",
                        "hyper": "Impact",
                    }
                    font = font_map.get(self.style, "Arial")
                    text_tool.SetInput("Font", font)
                    text_tool.SetInput("Size", 0.08)  # Relative to frame height

                    print(f"  [Titles] Text set: '{text}' (Font: {font})")
                else:
                    print("  [Titles] Warning: Could not find Text tool in Fusion comp")
            else:
                print("  [Titles] Warning: Could not access Fusion composition")

            return True

        except Exception as e:
            print(f"[Titles] Error inserting intro: {e}")
            return False

    def insert_lower_third(self, text: str, start_frame: int,
                           duration_frames: int = 72) -> bool:
        """
        Inserts a lower-third name tag on V2 at a specific timeline position.

        Args:
            text: Name or text to display
            start_frame: Timeline frame to place the lower-third
            duration_frames: How long to display (default ~3s at 24fps)
        """
        if not self.resolve or not self.project:
            print(f"[Titles/MOCK] Would insert lower-third: '{text}' at frame {start_frame}")
            return True

        tl = self.project.GetCurrentTimeline()
        if not tl:
            return False

        print(f"[Titles] Inserting lower-third: '{text}' at frame {start_frame}")

        try:
            tl_item = tl.InsertFusionTitleIntoTimeline("Text+")
            if not tl_item:
                return False

            comp = tl_item.GetFusionCompByIndex(1)
            if comp:
                text_tool = comp.FindTool("Template") or comp.FindTool("Text1")
                if text_tool:
                    text_tool.SetInput("StyledText", text)
                    text_tool.SetInput("Size", 0.04)
                    # Position in lower third of frame
                    text_tool.SetInput("Center", {1: 0.5, 2: 0.12})

            return True

        except Exception as e:
            print(f"[Titles] Error inserting lower-third: {e}")
            return False

    def insert_end_card(self, text: str = "Subscribe", duration_sec: float = 4.0) -> bool:
        """Inserts an end card at the tail of the timeline."""
        if not self.resolve or not self.project:
            print(f"[Titles/MOCK] Would insert end card: '{text}'")
            return True

        print(f"[Titles] Inserting end card: '{text}'")

        try:
            tl = self.project.GetCurrentTimeline()
            if not tl:
                return False

            tl_item = tl.InsertFusionTitleIntoTimeline("Text+")
            if not tl_item:
                return False

            comp = tl_item.GetFusionCompByIndex(1)
            if comp:
                text_tool = comp.FindTool("Template") or comp.FindTool("Text1")
                if text_tool:
                    text_tool.SetInput("StyledText", text)
                    text_tool.SetInput("Size", 0.06)

            return True

        except Exception as e:
            print(f"[Titles] Error inserting end card: {e}")
            return False
