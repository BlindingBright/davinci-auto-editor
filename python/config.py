import os
import tempfile

# ---- Directory Settings ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(tempfile.gettempdir(), "davinci_auto_editor")
os.makedirs(TEMP_DIR, exist_ok=True)

# ---- FPV Analysis Settings ----
FPV_N_SAMPLES = 20
FPV_TARGET_RES = (160, 90)
FPV_MOTION_THRESHOLD_MULT = 1.3  # Median * mult
FPV_MIN_THRESHOLD = 6.0
FPV_MIN_SEGMENT_DUR = 2.0

# ---- Audio Analysis Settings ----
WHISPER_MODEL = "base"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_VAD_MIN_SILENCE = 500

# ---- Editing Styles & Cut Lengths ----
STYLE_CUT_LENGTHS = {
    "reel":      {"aroll": 2.5, "fpv": 4.0, "broll": 2.0},
    "vlog":      {"aroll": 6.0, "fpv": 6.0, "broll": 4.0},
    "cinematic": {"aroll": 5.0, "fpv": 8.0, "broll": 4.0},
    "hyper":     {"aroll": 1.0, "fpv": 1.0, "broll": 0.4},
}

# ---- Music Sourcing ----
YT_SEARCH_QUERIES = {
    "vlog": "ytsearch1: ncs relaxed vlog music no copyright",
    "reel": "ytsearch1: ncs upbeat fast reel music no copyright short",
    "cinematic": "ytsearch1: ncs cinematic epic background music no copyright"
}

# ---- Resolve Settings ----
DEFAULT_TIMELINE_NAME = "Auto_Sequence_1"
DEFAULT_LUT_PATH = os.path.join(BASE_DIR, "assets", "cinematic.cube")
