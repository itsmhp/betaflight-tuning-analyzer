"""
Tuning Presets & Quad Profiles.

Provides pre-defined tuning presets (like KISS firmware presets) and
context-aware recommendations based on quad hardware specifications.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


# =====================================================================
# Quad Hardware Profile – user-provided hardware info
# =====================================================================

class FrameSize(Enum):
    """Common frame sizes."""
    WHOOP_65MM = "65mm"
    WHOOP_75MM = "75mm"
    TOOTHPICK_3INCH = "3inch"
    CINEWHOOP_3INCH = "3inch_cinewhoop"
    MICRO_4INCH = "4inch"
    FREESTYLE_5INCH = "5inch"
    RACE_5INCH = "5inch_race"
    LONG_RANGE_6INCH = "6inch"
    LONG_RANGE_7INCH = "7inch"
    X_CLASS_8INCH = "8inch_plus"
    UNKNOWN = "unknown"


class PropSize(Enum):
    """Common prop sizes."""
    P31MM = "31mm"
    P40MM = "40mm"
    P3016 = "3016"
    P3018 = "3018"
    P3520 = "3520"
    P4024 = "4024"
    P51_TRIBLADE = "5.1x3"
    P5040 = "5040"
    P5043 = "5043"
    P5045 = "5045"
    P5050 = "5050"
    P5130 = "51303"
    P6030 = "6030"
    P7035 = "7035"
    CUSTOM = "custom"


class FlyingStyle(Enum):
    """Intended flying style – determines tuning aggression."""
    CINEMATIC = "cinematic"
    FREESTYLE = "freestyle"
    RACING = "racing"
    LR_CRUISE = "long_range"


class PresetLevel(Enum):
    """Tuning aggression level (similar to KISS presets)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class QuadProfile:
    """User-supplied quad hardware description."""
    frame_size: str = ""          # e.g. "5inch", "3inch_cinewhoop"
    prop_size: str = ""           # e.g. "5045", "3018"
    prop_pitch: str = ""          # e.g. "4.3", "4.5"
    battery_cells: int = 0        # e.g. 4 (for 4S), 6 (for 6S)
    fc_name: str = ""             # e.g. "SpeedyBee F405 V4"
    esc_name: str = ""            # e.g. "SpeedyBee BLS 55A"
    esc_protocol: str = ""        # e.g. "DSHOT300", "DSHOT600"
    motor_kv: int = 0             # e.g. 1960, 2400
    weight_grams: int = 0         # AUW (all-up weight) in grams
    flying_style: str = "freestyle"
    preset_level: str = "medium"  # low / medium / high / ultra

    @property
    def is_provided(self) -> bool:
        """Return True if user provided any meaningful info."""
        return bool(self.frame_size or self.battery_cells or self.weight_grams)

    @property
    def inferred_class(self) -> str:
        """Infer quad class from frame size + weight."""
        if self.frame_size:
            return self.frame_size
        if self.weight_grams:
            if self.weight_grams < 60:
                return "65mm"
            elif self.weight_grams < 150:
                return "75mm"
            elif self.weight_grams < 250:
                return "3inch"
            elif self.weight_grams < 400:
                return "4inch"
            elif self.weight_grams < 700:
                return "5inch"
            else:
                return "6inch"
        return "5inch"  # sensible default


# =====================================================================
# Tuning Presets – pre-built tuning configurations
# =====================================================================

# Keys: (frame_class, preset_level)
# Values: dict of Betaflight CLI setting → value

TUNING_PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    # ============== 5-inch freestyle ==============
    "5inch": {
        "low": {
            "label": "5\" Low – Smooth Cinematic",
            "description": "Gentle, smooth response. Great for cinematic flying, "
                           "GoPro footage, and beginners. Low D-noise, cool motors.",
            "pid": {
                "p_roll": 38, "i_roll": 75, "d_roll": 32, "f_roll": 0,
                "p_pitch": 40, "i_pitch": 78, "d_pitch": 36, "f_pitch": 0,
                "p_yaw": 35, "i_yaw": 75, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 24, "d_min_pitch": 28,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 70, "dterm_lpf1_dyn_max_hz": 140,
                "dterm_lpf2_static_hz": 140,
            },
            "ff": {"feedforward_jitter_factor": 5, "feedforward_boost": 10},
            "rates": {"style": "cinematic"},
        },
        "medium": {
            "label": "5\" Medium – Balanced Freestyle",
            "description": "Balanced response for everyday freestyle. Good stick "
                           "feel with reasonable noise rejection.",
            "pid": {
                "p_roll": 45, "i_roll": 80, "d_roll": 40, "f_roll": 120,
                "p_pitch": 47, "i_pitch": 84, "d_pitch": 46, "f_pitch": 125,
                "p_yaw": 45, "i_yaw": 80, "d_yaw": 0, "f_yaw": 120,
                "d_min_roll": 30, "d_min_pitch": 34,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 75, "dterm_lpf1_dyn_max_hz": 150,
                "dterm_lpf2_static_hz": 150,
            },
            "ff": {"feedforward_jitter_factor": 7, "feedforward_boost": 15},
            "rates": {"style": "freestyle"},
        },
        "high": {
            "label": "5\" High – Aggressive Freestyle",
            "description": "Snappy response for aggressive freestyle. Higher PIDs, "
                           "more feedforward. Motors may run warmer.",
            "pid": {
                "p_roll": 55, "i_roll": 90, "d_roll": 48, "f_roll": 160,
                "p_pitch": 58, "i_pitch": 95, "d_pitch": 52, "f_pitch": 165,
                "p_yaw": 55, "i_yaw": 90, "d_yaw": 0, "f_yaw": 140,
                "d_min_roll": 36, "d_min_pitch": 40,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 80, "dterm_lpf1_dyn_max_hz": 170,
                "dterm_lpf2_static_hz": 170,
            },
            "ff": {"feedforward_jitter_factor": 10, "feedforward_boost": 20},
            "rates": {"style": "freestyle"},
        },
        "ultra": {
            "label": "5\" Ultra – Racing / Maximum Authority",
            "description": "Maximum authority and stick response. High PIDs, high FF. "
                           "Requires clean build and good motor/ESC setup.",
            "pid": {
                "p_roll": 65, "i_roll": 95, "d_roll": 52, "f_roll": 200,
                "p_pitch": 68, "i_pitch": 100, "d_pitch": 56, "f_pitch": 210,
                "p_yaw": 60, "i_yaw": 95, "d_yaw": 0, "f_yaw": 160,
                "d_min_roll": 40, "d_min_pitch": 44,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 90, "dterm_lpf1_dyn_max_hz": 185,
                "dterm_lpf2_static_hz": 185,
            },
            "ff": {"feedforward_jitter_factor": 12, "feedforward_boost": 25},
            "rates": {"style": "racing"},
        },
    },

    # ============== 5-inch race ==============
    "5inch_race": {
        "low": {
            "label": "5\" Race Low – Smooth Corners",
            "description": "Clean race tune with smooth cornering. Lower latency filters.",
            "pid": {
                "p_roll": 42, "i_roll": 70, "d_roll": 28, "f_roll": 130,
                "p_pitch": 44, "i_pitch": 73, "d_pitch": 32, "f_pitch": 135,
                "p_yaw": 38, "i_yaw": 70, "d_yaw": 0, "f_yaw": 100,
                "d_min_roll": 22, "d_min_pitch": 26,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 80, "dterm_lpf1_dyn_max_hz": 160,
                "dterm_lpf2_static_hz": 160,
            },
            "ff": {"feedforward_jitter_factor": 10, "feedforward_boost": 20},
            "rates": {"style": "racing"},
        },
        "medium": {
            "label": "5\" Race Medium – Balanced Race",
            "description": "Standard race tune with good cornering and straight-line speed.",
            "pid": {
                "p_roll": 50, "i_roll": 70, "d_roll": 30, "f_roll": 150,
                "p_pitch": 52, "i_pitch": 73, "d_pitch": 34, "f_pitch": 155,
                "p_yaw": 40, "i_yaw": 70, "d_yaw": 0, "f_yaw": 100,
                "d_min_roll": 25, "d_min_pitch": 28,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 85, "dterm_lpf1_dyn_max_hz": 170,
                "dterm_lpf2_static_hz": 170,
            },
            "ff": {"feedforward_jitter_factor": 12, "feedforward_boost": 25},
            "rates": {"style": "racing"},
        },
        "high": {
            "label": "5\" Race High – Aggressive Race",
            "description": "Sharp, snappy race tune. Requires clean build.",
            "pid": {
                "p_roll": 58, "i_roll": 75, "d_roll": 35, "f_roll": 180,
                "p_pitch": 60, "i_pitch": 78, "d_pitch": 38, "f_pitch": 185,
                "p_yaw": 50, "i_yaw": 75, "d_yaw": 0, "f_yaw": 130,
                "d_min_roll": 28, "d_min_pitch": 32,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 90, "dterm_lpf1_dyn_max_hz": 180,
                "dterm_lpf2_static_hz": 180,
            },
            "ff": {"feedforward_jitter_factor": 14, "feedforward_boost": 30},
            "rates": {"style": "racing"},
        },
        "ultra": {
            "label": "5\" Race Ultra – Maximum Performance",
            "description": "Absolute max performance. Very clean build required.",
            "pid": {
                "p_roll": 68, "i_roll": 80, "d_roll": 40, "f_roll": 220,
                "p_pitch": 70, "i_pitch": 84, "d_pitch": 44, "f_pitch": 225,
                "p_yaw": 55, "i_yaw": 80, "d_yaw": 0, "f_yaw": 160,
                "d_min_roll": 32, "d_min_pitch": 36,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 100, "dterm_lpf1_dyn_max_hz": 200,
                "dterm_lpf2_static_hz": 200,
            },
            "ff": {"feedforward_jitter_factor": 16, "feedforward_boost": 35},
            "rates": {"style": "racing"},
        },
    },

    # ============== 3-inch cinewhoop ==============
    "3inch_cinewhoop": {
        "low": {
            "label": "3\" CineWhoop Low – Ultra Smooth",
            "description": "Buttery smooth for indoor/proximity. Zero feedforward. Cool motors.",
            "pid": {
                "p_roll": 55, "i_roll": 95, "d_roll": 42, "f_roll": 0,
                "p_pitch": 58, "i_pitch": 100, "d_pitch": 48, "f_pitch": 0,
                "p_yaw": 50, "i_yaw": 95, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 30, "d_min_pitch": 35,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 60, "dterm_lpf1_dyn_max_hz": 130,
                "dterm_lpf2_static_hz": 130,
            },
            "ff": {"feedforward_jitter_factor": 3, "feedforward_boost": 0},
            "rates": {"style": "cinematic"},
        },
        "medium": {
            "label": "3\" CineWhoop Medium – Balanced",
            "description": "Good balance of smooth video and responsive control.",
            "pid": {
                "p_roll": 65, "i_roll": 100, "d_roll": 50, "f_roll": 0,
                "p_pitch": 68, "i_pitch": 105, "d_pitch": 55, "f_pitch": 0,
                "p_yaw": 60, "i_yaw": 100, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 35, "d_min_pitch": 40,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 70, "dterm_lpf1_dyn_max_hz": 140,
                "dterm_lpf2_static_hz": 140,
            },
            "ff": {"feedforward_jitter_factor": 5, "feedforward_boost": 5},
            "rates": {"style": "cinematic"},
        },
        "high": {
            "label": "3\" CineWhoop High – Responsive",
            "description": "More responsive cinewhoop tune for faster proximity flying.",
            "pid": {
                "p_roll": 75, "i_roll": 110, "d_roll": 58, "f_roll": 80,
                "p_pitch": 78, "i_pitch": 115, "d_pitch": 62, "f_pitch": 85,
                "p_yaw": 70, "i_yaw": 105, "d_yaw": 0, "f_yaw": 60,
                "d_min_roll": 40, "d_min_pitch": 45,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 75, "dterm_lpf1_dyn_max_hz": 150,
                "dterm_lpf2_static_hz": 150,
            },
            "ff": {"feedforward_jitter_factor": 7, "feedforward_boost": 10},
            "rates": {"style": "freestyle"},
        },
        "ultra": {
            "label": "3\" CineWhoop Ultra – Maximum",
            "description": "Maximum response for 3\" cinewhoop. Sharp handling.",
            "pid": {
                "p_roll": 85, "i_roll": 120, "d_roll": 65, "f_roll": 120,
                "p_pitch": 88, "i_pitch": 125, "d_pitch": 70, "f_pitch": 125,
                "p_yaw": 80, "i_yaw": 110, "d_yaw": 0, "f_yaw": 90,
                "d_min_roll": 45, "d_min_pitch": 50,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 80, "dterm_lpf1_dyn_max_hz": 160,
                "dterm_lpf2_static_hz": 160,
            },
            "ff": {"feedforward_jitter_factor": 10, "feedforward_boost": 15},
            "rates": {"style": "freestyle"},
        },
    },

    # ============== 3-inch toothpick/micro ==============
    "3inch": {
        "low": {
            "label": "3\" Micro Low – Gentle",
            "description": "Gentle tune for lightweight 3\" builds and toothpicks.",
            "pid": {
                "p_roll": 48, "i_roll": 85, "d_roll": 38, "f_roll": 80,
                "p_pitch": 50, "i_pitch": 90, "d_pitch": 42, "f_pitch": 85,
                "p_yaw": 42, "i_yaw": 80, "d_yaw": 0, "f_yaw": 60,
                "d_min_roll": 28, "d_min_pitch": 32,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 70, "dterm_lpf1_dyn_max_hz": 140,
                "dterm_lpf2_static_hz": 140,
            },
            "ff": {"feedforward_jitter_factor": 5, "feedforward_boost": 10},
            "rates": {"style": "freestyle"},
        },
        "medium": {
            "label": "3\" Micro Medium – Balanced",
            "description": "Balanced 3\" tune for freestyle with smaller quads.",
            "pid": {
                "p_roll": 55, "i_roll": 90, "d_roll": 45, "f_roll": 100,
                "p_pitch": 58, "i_pitch": 95, "d_pitch": 50, "f_pitch": 105,
                "p_yaw": 50, "i_yaw": 85, "d_yaw": 0, "f_yaw": 80,
                "d_min_roll": 30, "d_min_pitch": 34,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 75, "dterm_lpf1_dyn_max_hz": 150,
                "dterm_lpf2_static_hz": 150,
            },
            "ff": {"feedforward_jitter_factor": 7, "feedforward_boost": 15},
            "rates": {"style": "freestyle"},
        },
        "high": {
            "label": "3\" Micro High – Aggressive",
            "description": "Aggressive 3\" tune. Snappy handling for experienced pilots.",
            "pid": {
                "p_roll": 65, "i_roll": 100, "d_roll": 52, "f_roll": 130,
                "p_pitch": 68, "i_pitch": 105, "d_pitch": 56, "f_pitch": 135,
                "p_yaw": 60, "i_yaw": 95, "d_yaw": 0, "f_yaw": 100,
                "d_min_roll": 36, "d_min_pitch": 40,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 80, "dterm_lpf1_dyn_max_hz": 160,
                "dterm_lpf2_static_hz": 160,
            },
            "ff": {"feedforward_jitter_factor": 10, "feedforward_boost": 20},
            "rates": {"style": "freestyle"},
        },
        "ultra": {
            "label": "3\" Micro Ultra – Maximum",
            "description": "Max performance for 3\" micro quads. Clean build required.",
            "pid": {
                "p_roll": 75, "i_roll": 110, "d_roll": 58, "f_roll": 160,
                "p_pitch": 78, "i_pitch": 115, "d_pitch": 62, "f_pitch": 165,
                "p_yaw": 70, "i_yaw": 105, "d_yaw": 0, "f_yaw": 120,
                "d_min_roll": 42, "d_min_pitch": 46,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 85, "dterm_lpf1_dyn_max_hz": 170,
                "dterm_lpf2_static_hz": 170,
            },
            "ff": {"feedforward_jitter_factor": 12, "feedforward_boost": 25},
            "rates": {"style": "racing"},
        },
    },

    # ============== Whoop (65/75mm) ==============
    "65mm": {
        "low": {
            "label": "Tiny Whoop Low – Gentle Indoor",
            "description": "Gentle indoor flying with smooth handling.",
            "pid": {
                "p_roll": 60, "i_roll": 110, "d_roll": 48, "f_roll": 0,
                "p_pitch": 65, "i_pitch": 115, "d_pitch": 52, "f_pitch": 0,
                "p_yaw": 55, "i_yaw": 110, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 35, "d_min_pitch": 40,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 60, "dterm_lpf1_dyn_max_hz": 120,
                "dterm_lpf2_static_hz": 120,
            },
            "ff": {"feedforward_jitter_factor": 3, "feedforward_boost": 0},
            "rates": {"style": "cinematic"},
        },
        "medium": {
            "label": "Tiny Whoop Medium – Balanced",
            "description": "Standard whoop tune for mixed indoor/outdoor flying.",
            "pid": {
                "p_roll": 70, "i_roll": 120, "d_roll": 55, "f_roll": 0,
                "p_pitch": 75, "i_pitch": 125, "d_pitch": 60, "f_pitch": 0,
                "p_yaw": 70, "i_yaw": 120, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 40, "d_min_pitch": 45,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 65, "dterm_lpf1_dyn_max_hz": 130,
                "dterm_lpf2_static_hz": 130,
            },
            "ff": {"feedforward_jitter_factor": 5, "feedforward_boost": 5},
            "rates": {"style": "freestyle"},
        },
        "high": {
            "label": "Tiny Whoop High – Snappy",
            "description": "Snappy whoop tune for racing and trick flying.",
            "pid": {
                "p_roll": 85, "i_roll": 130, "d_roll": 62, "f_roll": 80,
                "p_pitch": 90, "i_pitch": 135, "d_pitch": 68, "f_pitch": 85,
                "p_yaw": 80, "i_yaw": 125, "d_yaw": 0, "f_yaw": 60,
                "d_min_roll": 48, "d_min_pitch": 52,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 70, "dterm_lpf1_dyn_max_hz": 140,
                "dterm_lpf2_static_hz": 140,
            },
            "ff": {"feedforward_jitter_factor": 8, "feedforward_boost": 10},
            "rates": {"style": "freestyle"},
        },
        "ultra": {
            "label": "Tiny Whoop Ultra – Maximum",
            "description": "Maximum response for tiny whoop racing.",
            "pid": {
                "p_roll": 95, "i_roll": 140, "d_roll": 70, "f_roll": 120,
                "p_pitch": 100, "i_pitch": 145, "d_pitch": 75, "f_pitch": 125,
                "p_yaw": 90, "i_yaw": 135, "d_yaw": 0, "f_yaw": 90,
                "d_min_roll": 55, "d_min_pitch": 60,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 75, "dterm_lpf1_dyn_max_hz": 150,
                "dterm_lpf2_static_hz": 150,
            },
            "ff": {"feedforward_jitter_factor": 10, "feedforward_boost": 15},
            "rates": {"style": "racing"},
        },
    },

    # ============== Long Range 6-7 inch ==============
    "6inch": {
        "low": {
            "label": "6\"+ LR Low – Efficiency Focus",
            "description": "Smooth, efficient long range tune. Minimal D-term noise.",
            "pid": {
                "p_roll": 35, "i_roll": 70, "d_roll": 28, "f_roll": 0,
                "p_pitch": 38, "i_pitch": 73, "d_pitch": 32, "f_pitch": 0,
                "p_yaw": 30, "i_yaw": 70, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 20, "d_min_pitch": 24,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 60, "dterm_lpf1_dyn_max_hz": 120,
                "dterm_lpf2_static_hz": 120,
            },
            "ff": {"feedforward_jitter_factor": 3, "feedforward_boost": 0},
            "rates": {"style": "cinematic"},
        },
        "medium": {
            "label": "6\"+ LR Medium – Balanced",
            "description": "Balanced long range tune with decent freestyle capability.",
            "pid": {
                "p_roll": 42, "i_roll": 78, "d_roll": 35, "f_roll": 80,
                "p_pitch": 44, "i_pitch": 82, "d_pitch": 38, "f_pitch": 85,
                "p_yaw": 38, "i_yaw": 75, "d_yaw": 0, "f_yaw": 60,
                "d_min_roll": 25, "d_min_pitch": 28,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 65, "dterm_lpf1_dyn_max_hz": 130,
                "dterm_lpf2_static_hz": 130,
            },
            "ff": {"feedforward_jitter_factor": 5, "feedforward_boost": 8},
            "rates": {"style": "long_range"},
        },
        "high": {
            "label": "6\"+ LR High – Active Flying",
            "description": "More responsive LR tune for active flying and freestyle-LR.",
            "pid": {
                "p_roll": 50, "i_roll": 85, "d_roll": 42, "f_roll": 120,
                "p_pitch": 52, "i_pitch": 88, "d_pitch": 45, "f_pitch": 125,
                "p_yaw": 45, "i_yaw": 82, "d_yaw": 0, "f_yaw": 90,
                "d_min_roll": 30, "d_min_pitch": 34,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 70, "dterm_lpf1_dyn_max_hz": 140,
                "dterm_lpf2_static_hz": 140,
            },
            "ff": {"feedforward_jitter_factor": 7, "feedforward_boost": 12},
            "rates": {"style": "freestyle"},
        },
        "ultra": {
            "label": "6\"+ LR Ultra – Maximum Authority",
            "description": "Maximum authority for large props. Clean build and balance essential.",
            "pid": {
                "p_roll": 58, "i_roll": 92, "d_roll": 48, "f_roll": 150,
                "p_pitch": 60, "i_pitch": 95, "d_pitch": 52, "f_pitch": 155,
                "p_yaw": 52, "i_yaw": 88, "d_yaw": 0, "f_yaw": 110,
                "d_min_roll": 35, "d_min_pitch": 38,
            },
            "filter": {
                "dterm_lpf1_dyn_min_hz": 75, "dterm_lpf1_dyn_max_hz": 150,
                "dterm_lpf2_static_hz": 150,
            },
            "ff": {"feedforward_jitter_factor": 10, "feedforward_boost": 18},
            "rates": {"style": "freestyle"},
        },
    },
}

# Alias 75mm whoops to use same presets as 65mm
TUNING_PRESETS["75mm"] = TUNING_PRESETS["65mm"]
# Alias 4inch to use 3inch presets
TUNING_PRESETS["4inch"] = TUNING_PRESETS["3inch"]
# Alias 7inch to 6inch
TUNING_PRESETS["7inch"] = TUNING_PRESETS["6inch"]
# Alias 8inch+
TUNING_PRESETS["8inch_plus"] = TUNING_PRESETS["6inch"]


def get_preset(frame_class: str, level: str) -> Optional[Dict[str, Any]]:
    """Get a tuning preset by frame class and aggression level."""
    fc = frame_class.lower()
    lvl = level.lower()
    if fc in TUNING_PRESETS and lvl in TUNING_PRESETS[fc]:
        return TUNING_PRESETS[fc][lvl]
    # Fallback to 5inch
    if lvl in TUNING_PRESETS.get("5inch", {}):
        return TUNING_PRESETS["5inch"][lvl]
    return None


def get_all_presets_for_size(frame_class: str) -> Dict[str, Dict[str, Any]]:
    """Get all preset levels for a given frame class."""
    fc = frame_class.lower()
    return TUNING_PRESETS.get(fc, TUNING_PRESETS.get("5inch", {}))


def generate_preset_cli(preset: Dict[str, Any], pid_profile: int = 0) -> str:
    """Generate CLI commands from a preset dict."""
    lines = []
    lines.append(f"profile {pid_profile}")
    lines.append("")

    if "pid" in preset:
        lines.append("# PID Values")
        for key, val in preset["pid"].items():
            lines.append(f"set {key} = {val}")
        lines.append("")

    if "filter" in preset:
        lines.append("# Filter Settings")
        for key, val in preset["filter"].items():
            lines.append(f"set {key} = {val}")
        lines.append("")

    if "ff" in preset:
        lines.append("# Feedforward")
        for key, val in preset["ff"].items():
            lines.append(f"set {key} = {val}")
        lines.append("")

    lines.append("save")
    return "\n".join(lines)
