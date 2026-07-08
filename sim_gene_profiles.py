#!/usr/bin/env python3
"""CaseOh90000 SIM Gene Lab profile support.

This module edits *only the copied branch* data/genes.xml. It is designed for
SIM9000 experimentation, not permanent vanilla save editing.

The profile system works by changing how gene values express in the copied
branch. It does not rewrite any submitted DNA strings. That makes it useful for
asking SIM9000 questions like "what if this run only expressed car-like body
plan genes?" or "what if every helix used the tail-power profile?" without
making users hand-edit 40 DNA lines.
"""
from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from caseoh import CASEOH_TARGETS
except Exception:  # pragma: no cover
    CASEOH_TARGETS = {}
try:
    from exploding_seed import EXPLODING_FINISHER_SEED_DNA
except Exception:  # pragma: no cover
    EXPLODING_FINISHER_SEED_DNA = ''

# Positional helix map for the public Horsey build. This is the real DNA
# position map used by the earlier simulator work; it is not the order of
# genes.xml. H18P01 is SPEED_FACTOR, H08P04 is LEG_STRENGTH, etc.
HELIX_GENE_NAMES: List[List[str]] = [
    ['BONES', 'BONES2', 'OSTODERM', 'OSTO_SIZE', 'GIANT_DWARF', 'TAIL_BOTTOM', 'LEG_STRETCH2', 'ARM_STRETCH2', 'HEAD_THICK_SKULL', 'NECK_STIFF'],
    ['GUT', 'GUT_IS_UDDER', 'DERRIERE', 'LEG_IS_CIRCLE', 'FOOT_IS_CIRCLE', 'TONGUE', 'TONGUE_SEGS', 'BELLY_ALT', 'PAT_BELLY', 'LITTER_SIZE', 'OLD_AGE', 'OMNIVORE', 'LIMP'],
    ['MUSCLE_USE', 'TAIL_STIFF', 'LEG_FLEXIBILITY', 'LEG_FLEX_BIAS', 'TAIL_FLEXIBILITY', 'TAIL_SPEED', 'LEG_AND_ARM_LIMP', 'ARM_STRENGTH', 'ARM_FLEXIBILITY', 'ARM_FLEX_BIAS', 'NECK_FLEXIBILITY', 'NECK_FLEX_BIAS', 'BRAIN_SPASTIC'],
    ['SPLAY', 'LEG_IN', 'LEG_IN2', 'TAIL_ANGLE', 'TAIL_JOINT_TYPE', 'LEG_JOINT_TYPE', 'HAS_KNEE', 'KNEE_MIN', 'KNEE_MAX', 'ARM_JOINT_TYPE', 'HAS_ELBOW', 'ELBOW_RANGE', 'NECK_JOINT_TYPE', 'HEAD_JOINTED', 'STIFF_JOINTS'],
    ['LEG_TAG', 'LEG_HAS_FOOT', 'LEG_COUNT', 'LEG_THRUST_BACK', 'ARM_TAG', 'ARM_HAS_HAND', 'NECK_TAG', 'NECK_SLOUCH', 'NECK_ONTOP', 'BREAK_FORCE', 'EAR_X'],
    ['QUADRUPED', 'BIPED', 'UPARM_TAG', 'UPARM_Y', 'UPARM_GOOFY', 'ARM_FORWARD', 'UPARM_ANGLE', 'WHITE_IS_LETHAL'],
    ['SIZE', 'ASPECT', 'SKINNY', 'CHEST_BIG', 'CHEST_SMALL', 'NECK_TYPE', 'NECK_LENGTH', 'NECK_GIRAFFE', 'NECK_THICKNESS', 'NECK_ANGLE', 'NECK_COCK'],
    ['TAIL_TAG', 'TAIL_EXISTS', 'TAIL_SIZE', 'TAIL_SHORT', 'TAIL_ASPECT', 'TAIL_SHAPE', 'TAIL_SEGMENTS', 'TAIL_WAG'],
    ['LEG_TYPE', 'LEG_LENGTH', 'LEG_STRETCH', 'LEG_SKEW', 'LEG_STRENGTH', 'LEG_PENCIL', 'ARM_TYPE', 'ARM_LENGTH', 'ARM_STRETCH', 'ARM_SKEW', 'ARM_NODE_SCALE'],
    ['HAS_FOOT', 'FOOT_SIZE', 'FOOT_CLOWN', 'FOOT_THICKNESS', 'FOOT_TOE', 'FOOT_BACKWARDS', 'HAS_HAND', 'HAND_WIDTH', 'HAND_LENGTH', 'HAND_FINGER', 'SKIN_HANDS'],
    ['HEAD_SIZE', 'HEAD_X_GROWTH', 'HEAD_Y_GROWTH', 'HEAD_ASPECT', 'HEAD_SQUARE', 'HEAD_HAS_BACK', 'HEAD_GIANT', 'HEAD_SHRUNK', 'HEAD_CHIMERA', 'EYEBOX_X', 'EYEBOX_Y', 'EYEBOX_SIZE', 'SKIN_HEAD'],
    ['EYE_STYLE', 'BUGEYE', 'EYE_SIZE', 'PUPIL_SIZE', 'HAS_PUPIL', 'BROW_SIZE', 'BROW_SLANT', 'EYE_HUE', 'EAR_STYLE', 'EAR_SHAPE', 'EAR_SIZE', 'EAR_ASPECT', 'EAR_SLANT', 'EAR_INTERIOR', 'EAR_FLOP'],
    ['TEETH_SHAPE', 'HAS_MOUTH', 'MOUTH_Y', 'MOUTH_SIZE', 'JAW', 'TEETH_UPPER', 'TEETH_UPPER2', 'NOSE_STYLE', 'NOSE_INNY', 'NOSE_Y', 'NOSE_SIZE', 'NOSE_INTERIOR', 'FLU_IMMUNITY'],
    ['HAS_ANTLERS', 'ANTLER_X', 'ANTLER_W', 'ANTLER_H', 'ANTLER_TAPER', 'ANTLER_POM', 'ANTLER_COLOR', 'POM_COLOR', 'POM_USECOLOR', 'HAT_POM', 'HAT_POM_IS_LID'],
    ['ANTLER_REC', 'ANTLER_REC2', 'ANTLER_FLIP', 'ANTLER_MOD', 'ANTLER_SCALEH', 'ANTLER_SCALEW', 'ANTLER_ANGLE', 'ANTLER_ANGLE2', 'ANTLER_ANGLE_RAND', 'ANTLER_T1', 'ANTLER_T2'],
    ['HAT_EXISTS', 'HAT_SIZE', 'HAT_RAKE', 'HAT_ASPECT', 'HAT_TAPER', 'HAT_CLONE', 'HAT_BACK_SCALE', 'HAT_FRONT_SCALE', 'HAT_BACK_ANGLE', 'HAT_FRONT_ANGLE', 'HAT_ANGLE_RAND', 'HAT_FLIP', 'HAT_T'],
    ['BASE_BROWN', 'BASE_BLACK', 'BASE_RED', 'BASE_GREEN', 'GREEN_KNOCKOUT', 'BASE_CREAM', 'ALT_BLUE', 'SPOT_YELLOW', 'SKIN_HUE', 'SKIN_HUE2', 'SWAP_BASE_SPOT', 'SWAP_ALT_SPOT', 'WHITE', 'NOSE_HUE', 'HOOF_COLOR'],
    ['AGOUTI', 'FOOT_IS_HOOF', 'RACCOON_EYE', 'EAR_COMP', 'TAIL_ALT', 'PAT_SPLIT', 'PAT_STRIPE', 'PAT_SPOT', 'PAT_PERLIN', 'PAT_PERLIN2', 'PAT_PERLIN_SIZE'],
    ['NARCOLEPSY', 'SPEED_FACTOR', 'NECK_SPEED', 'RAMPAGE', 'SPINAL_LOCO', 'HIGH_INTELLECT', 'L_LEG_SIGNAL', 'L_ARM_SIGNAL', 'L_TAIL_SIGNAL', 'L_NECK_SIGNAL', 'LOCO_SYNC'],
    ['L_LEG_FTOB_REACT', 'L_LEG_FTOB_EVENT', 'L_LEG_BTOF_REACT', 'L_LEG_BTOF_EVENT', 'L_ARM_FTOB_REACT', 'L_ARM_FTOB_EVENT', 'L_ARM_BTOF_REACT', 'L_ARM_BTOF_EVENT', 'L_TAIL_FTOB_REACT', 'L_TAIL_FTOB_EVENT', 'L_TAIL_BTOF_REACT', 'L_TAIL_BTOF_EVENT', 'L_NECK_FTOB_REACT', 'L_NECK_FTOB_EVENT', 'L_NECK_BTOF_REACT', 'L_NECK_BTOF_EVENT'],
]
HELIX_RANGES: Dict[str, Tuple[int, int]] = {f"{i:02d}": (0, len(row)) for i, row in enumerate(HELIX_GENE_NAMES)}

# Names shown in the panel. "Any / no lock" intentionally does nothing.
SPECIES_PROFILES = [
    "Any / no species lock",
    "Horse",
    "Car",
    "Human-ish",
    "Giraffe",
    "Rabbit",
    "Impala",
    "Centipede",
    "Alligator",
    "Tiny critter",
    "Freak / mixed",
]

RACING_PRESETS = [
    "None / normal genes",
    "Clean racer",
    "Car mode",
    "Roll mode",
    "Legless mode",
    "Tail power mode",
    "Tiny horse mode",
    "Launch-angle tire racer",
    "No-glitch intact racer",
]

HELIX_PRESETS = [
    "Unchanged",
    "Clean racer",
    "Car/wheels",
    "Roll",
    "Legless",
    "Tail power",
    "Tiny horse",
    "Stable/no-glitch",
]

# Helper target dictionaries. Values are expression values written into g0-g3.
# This biases or locks the phenotype without changing DNA strings.
CORE_RACE: Dict[str, int] = {
    "SPEED_FACTOR": 133,
    "NARCOLEPSY": 0,
    "SPINAL_LOCO": 2,
    "LOCO_SYNC": 1,
    "LEG_STRENGTH": 120,
    "LEG_LENGTH": 120,
    "BREAK_FORCE": 0,
    "MUSCLE_USE": 100,
    "FLU_IMMUNITY": 1,
}

CAR_WHEELS: Dict[str, int] = {
    **CORE_RACE,
    "QUADRUPED": 1,
    "BIPED": 0,
    "SIZE": 75,
    "SKINNY": 75,
    "GIANT_DWARF": 100,
    "LEG_TYPE": 1,
    "LEG_COUNT": 1,
    "LEG_HAS_FOOT": 1,
    "HAS_FOOT": 1,
    "LEG_IS_CIRCLE": 1,
    "FOOT_IS_CIRCLE": 1,
    "FOOT_SIZE": 20,
    "FOOT_THICKNESS": 15,
    "FOOT_BACKWARDS": 0,
    "FOOT_IS_HOOF": 0,
    "LEG_STRETCH": 14,
    "LEG_STRETCH2": 0,
    "LEG_SKEW": 0,
    "LEG_THRUST_BACK": 1,
    "NECK_STIFF": 1,
    "STIFF_JOINTS": 18,
}

ROLL_MODE: Dict[str, int] = {
    **CAR_WHEELS,
    "ASPECT": 200,
    "BONES": 0,
    "BONES2": 0,
    "ARM_TYPE": 1,
    "ARM_HAS_HAND": 0,
    "ARM_LENGTH": 80,
    "ARM_STRENGTH": 120,
    "ARM_STRETCH": 0,
    "ARM_SKEW": 0,
    "HAS_HAND": 0,
}

LEGLESS_MODE: Dict[str, int] = {
    **CORE_RACE,
    "LEG_LENGTH": 50,
    "LEG_STRETCH": 0,
    "LEG_STRETCH2": 0,
    "LEG_HAS_FOOT": 0,
    "HAS_FOOT": 0,
    "FOOT_SIZE": 0,
    "FOOT_IS_CIRCLE": 0,
    "LEG_AND_ARM_LIMP": 0,
    "BREAK_FORCE": 0,
    "TAIL_EXISTS": 1,
    "TAIL_SIZE": 140,
    "TAIL_SHORT": 35,
    "TAIL_STIFF": 1,
}

TAIL_POWER: Dict[str, int] = {
    **CORE_RACE,
    "TAIL_EXISTS": 1,
    "TAIL_SIZE": 140,
    "TAIL_SHORT": 35,
    "TAIL_ASPECT": 50,
    "TAIL_ANGLE": 60,
    "TAIL_JOINT_TYPE": 1,
    "TAIL_STIFF": 1,
    "TAIL_SPEED": 200,
    "TAIL_FLEXIBILITY": 15,
    "TAIL_SEGMENTS": 5,
    "TAIL_WAG": 1,
    "L_TAIL_SIGNAL": 4,
    "L_TAIL_FTOB_REACT": 3,
    "L_TAIL_FTOB_EVENT": 4,
    "L_TAIL_BTOF_REACT": 3,
    "L_TAIL_BTOF_EVENT": 4,
}

TINY_HORSE: Dict[str, int] = {
    **CORE_RACE,
    "SIZE": 35,
    "GIANT_DWARF": 66,
    "SKINNY": 75,
    "ASPECT": 200,
    "CHEST_BIG": 102,
    "CHEST_SMALL": 95,
    "GUT": 0,
    "DERRIERE": 0,
    "LEG_LENGTH": 120,
    "LEG_STRENGTH": 120,
    "FOOT_SIZE": 0,
    "FOOT_THICKNESS": 7,
    "HEAD_SIZE": 75,
    "NECK_LENGTH": 60,
}

LAUNCH_TIRE: Dict[str, int] = {
    **CORE_RACE,
    "LEG_IS_CIRCLE": 1,
    "FOOT_IS_CIRCLE": 0,
    "FOOT_SIZE": 0,
    "FOOT_THICKNESS": 7,
    "FOOT_BACKWARDS": 1,
    "LEG_STRETCH": 14,
    "LEG_STRETCH2": 0,
    "LEG_SKEW": 0,
    "ARM_STRENGTH": 95,
    "ARM_LENGTH": 80,
    "NECK_STIFF": 0,
    "TAIL_EXISTS": 1,
    "TAIL_SIZE": 120,
    "TAIL_WAG": 0,
}

STABLE_INTACT: Dict[str, int] = {
    **CORE_RACE,
    "LEG_HAS_FOOT": 1,
    "HAS_FOOT": 1,
    "LEG_IS_CIRCLE": 0,
    "FOOT_IS_CIRCLE": 0,
    "LEG_STRETCH": 0,
    "LEG_STRETCH2": 0,
    "LEG_SKEW": 0,
    "LEG_AND_ARM_LIMP": 0,
    "STIFF_JOINTS": 0,
    "NECK_STIFF": 1,
    "TAIL_EXISTS": 1,
    "TAIL_WAG": 0,
}

SPECIES_TARGETS: Dict[str, Dict[str, int]] = {
    "Any / no species lock": {},
    "Freak / mixed": {},
    "Horse": {
        "QUADRUPED": 1, "BIPED": 0, "SIZE": 100, "GIANT_DWARF": 100, "SKINNY": 100,
        "LEG_TYPE": 1, "LEG_COUNT": 1, "LEG_LENGTH": 100, "LEG_HAS_FOOT": 1, "HAS_FOOT": 1,
        "FOOT_IS_HOOF": 1, "ARM_HAS_HAND": 0, "HAS_HAND": 0, "TAIL_EXISTS": 1, "TAIL_SIZE": 100,
        "NECK_LENGTH": 70, "HEAD_SIZE": 100,
    },
    "Car": {
        "QUADRUPED": 1, "BIPED": 0, "SIZE": 75, "GIANT_DWARF": 100, "SKINNY": 75,
        "LEG_TYPE": 1, "LEG_COUNT": 1, "LEG_HAS_FOOT": 1, "HAS_FOOT": 1, "LEG_IS_CIRCLE": 1,
        "FOOT_IS_CIRCLE": 1, "FOOT_IS_HOOF": 0, "BREAK_FORCE": 0, "NECK_STIFF": 1,
    },
    "Human-ish": {
        "QUADRUPED": 0, "BIPED": 1, "LEG_TYPE": 1, "LEG_COUNT": 1, "ARM_HAS_HAND": 1,
        "HAS_HAND": 1, "ARM_LENGTH": 80, "ARM_STRENGTH": 95, "TAIL_EXISTS": 0, "HEAD_SIZE": 100,
    },
    "Giraffe": {
        "QUADRUPED": 1, "BIPED": 0, "SIZE": 100, "GIANT_DWARF": 133, "LEG_LENGTH": 120,
        "NECK_GIRAFFE": 120, "NECK_LENGTH": 90, "NECK_THICKNESS": 95, "TAIL_EXISTS": 1,
    },
    "Rabbit": {
        "QUADRUPED": 1, "BIPED": 0, "SIZE": 50, "LEG_LENGTH": 120, "LEG_THRUST_BACK": 2,
        "EAR_SIZE": 40, "EAR_FLOP": 200, "TAIL_EXISTS": 1, "TAIL_SIZE": 80, "TAIL_SHORT": 35,
    },
    "Impala": {
        "QUADRUPED": 1, "BIPED": 0, "SIZE": 75, "LEG_LENGTH": 120, "LEG_STRENGTH": 120,
        "LEG_STRETCH": 14, "LEG_THRUST_BACK": 1, "TAIL_EXISTS": 1, "NECK_LENGTH": 70,
    },
    "Centipede": {
        "QUADRUPED": 1, "BIPED": 0, "SIZE": 50, "LEG_COUNT": 7, "LEG_LENGTH": 80,
        "LEG_HAS_FOOT": 1, "HAS_FOOT": 1, "TAIL_EXISTS": 0, "NECK_LENGTH": 30,
    },
    "Alligator": {
        "QUADRUPED": 1, "BIPED": 0, "SIZE": 100, "ASPECT": 310, "SKINNY": 75,
        "LEG_LENGTH": 50, "LEG_COUNT": 1, "TAIL_EXISTS": 1, "TAIL_SIZE": 140, "TAIL_SHORT": 35,
        "NECK_LENGTH": 30, "HEAD_SIZE": 133,
    },
    "Tiny critter": {
        "SIZE": 35, "GIANT_DWARF": 66, "SKINNY": 75, "LEG_LENGTH": 80, "HEAD_SIZE": 75,
        "FOOT_SIZE": 0, "TAIL_SIZE": 80,
    },
}

RACING_TARGETS: Dict[str, Dict[str, int]] = {
    "None / normal genes": {},
    "Clean racer": CORE_RACE,
    "Car mode": CAR_WHEELS,
    "Roll mode": ROLL_MODE,
    "Legless mode": LEGLESS_MODE,
    "Tail power mode": TAIL_POWER,
    "Tiny horse mode": TINY_HORSE,
    "Launch-angle tire racer": LAUNCH_TIRE,
    "No-glitch intact racer": STABLE_INTACT,
}

HELIX_TARGETS: Dict[str, Dict[str, int]] = {
    "Unchanged": {},
    "Clean racer": CORE_RACE,
    "Car/wheels": CAR_WHEELS,
    "Roll": ROLL_MODE,
    "Legless": LEGLESS_MODE,
    "Tail power": TAIL_POWER,
    "Tiny horse": TINY_HORSE,
    "Stable/no-glitch": STABLE_INTACT,
}


# ---------------------------------------------------------------------------
# v1.4 community archetype presets
# ---------------------------------------------------------------------------
# These replace the earlier abstract labels. They are based on common community
# racer language: fast wheeled horses, alligator/car wheel hybrids, tanks,
# oval wheel rollers, living Segway-like builds, tail launchers, tiny cars, and
# intact non-glitch racers. Values are expression targets for data/genes.xml;
# they do not rewrite DNA strings.
RACING_PRESETS = [
    "None / normal genes",
    "Clean speed horse",
    "Fast wheeled horse",
    "Tank / multi-wheel",
    "Oval wheel roller",
    "Living Segway",
    "Tail launcher",
    "Exploding finisher",
    "Tiny car",
    "No-glitch intact racer",
]

HELIX_PRESETS = [
    "Unchanged",
    "Speed core",
    "Wheel/contact",
    "Oval roller",
    "Tank/multi-wheel",
    "Tail launcher",
    "Exploding finisher",
    "Tiny car",
    "Intact/stable",
]

CLEAN_SPEED_HORSE: Dict[str, int] = {
    **CORE_RACE,
    "QUADRUPED": 1,
    "BIPED": 0,
    "LEG_HAS_FOOT": 1,
    "HAS_FOOT": 1,
    "LEG_IS_CIRCLE": 0,
    "FOOT_IS_CIRCLE": 0,
    "FOOT_IS_HOOF": 1,
    "LEG_STRETCH": 0,
    "LEG_SKEW": 0,
    "TAIL_EXISTS": 1,
    "TAIL_WAG": 0,
    "NECK_STIFF": 1,
}

FAST_WHEELED_HORSE: Dict[str, int] = {
    **CORE_RACE,
    "QUADRUPED": 1,
    "BIPED": 0,
    "LEG_TYPE": 1,
    "LEG_COUNT": 1,
    "LEG_JOINT_TYPE": 1,
    "LEG_IS_CIRCLE": 1,
    "FOOT_IS_CIRCLE": 1,
    "LEG_HAS_FOOT": 1,
    "HAS_FOOT": 1,
    "FOOT_IS_HOOF": 0,
    "FOOT_SIZE": 20,
    "FOOT_THICKNESS": 15,
    "FOOT_BACKWARDS": 0,
    "LEG_STRETCH": 0,
    "LEG_SKEW": 0,
    "TAIL_EXISTS": 1,
    "TAIL_SIZE": 120,
    "TAIL_WAG": 0,
    "NECK_STIFF": 1,
}

TANK_MULTI_WHEEL: Dict[str, int] = {
    **FAST_WHEELED_HORSE,
    "SIZE": 100,
    "GIANT_DWARF": 100,
    "SKINNY": 75,
    "LEG_COUNT": 7,
    "LEG_STRENGTH": 120,
    "ARM_STRENGTH": 120,
    "FOOT_SIZE": 30,
    "FOOT_THICKNESS": 15,
    "STIFF_JOINTS": 18,
}

OVAL_WHEEL_ROLLER: Dict[str, int] = {
    **FAST_WHEELED_HORSE,
    "LEG_STRETCH": 14,
    "LEG_SKEW": 24,
    "ARM_LENGTH": 80,
    "ARM_STRETCH": 14,
    "ARM_SKEW": 20,
    "ARM_STRENGTH": 120,
    "ASPECT": 200,
    "TAIL_EXISTS": 1,
    "TAIL_WAG": 0,
}

LIVING_SEGWAY: Dict[str, int] = {
    **FAST_WHEELED_HORSE,
    "SIZE": 75,
    "GIANT_DWARF": 100,
    "LEG_COUNT": 1,
    "FOOT_SIZE": 0,
    "FOOT_THICKNESS": 7,
    "FOOT_BACKWARDS": 1,
    "ARM_LENGTH": 80,
    "ARM_STRENGTH": 95,
    "NECK_STIFF": 0,
    "TAIL_EXISTS": 1,
    "TAIL_SIZE": 120,
    "TAIL_WAG": 0,
}

TAIL_LAUNCHER: Dict[str, int] = {
    **CORE_RACE,
    "TAIL_EXISTS": 1,
    "TAIL_SIZE": 140,
    "TAIL_SHORT": 35,
    "TAIL_ASPECT": 50,
    "TAIL_ANGLE": 60,
    "TAIL_JOINT_TYPE": 1,
    "TAIL_STIFF": 1,
    "TAIL_SPEED": 200,
    "TAIL_FLEXIBILITY": 15,
    "TAIL_SEGMENTS": 5,
    "TAIL_WAG": 1,
    "L_TAIL_SIGNAL": 4,
    "L_TAIL_FTOB_REACT": 3,
    "L_TAIL_FTOB_EVENT": 4,
    "L_TAIL_BTOF_REACT": 3,
    "L_TAIL_BTOF_EVENT": 4,
    # Fragile/low break force is intentional for the shotgun-part archetype.
    "BREAK_FORCE": 0,
}

EXPLODING_FINISHER: Dict[str, int] = {
    **CORE_RACE,
    # Anything-goes, public-community "spontaneous combustion" / part-finish archetype.
    # It deliberately defeats intact/no-glitch protection and biases toward violent
    # launch geometry: low break force, circle feet, high tail/limb/neck speed, and
    # asynchronous locomotion signals. Values use legal in-game gene expression bands.
    "BREAK_FORCE": 0,
    "RAMPAGE": 1,
    "BRAIN_SPASTIC": 2,
    "NECK_SPEED": 200,
    "STIFF_JOINTS": 50,
    "LEG_AND_ARM_LIMP": 1,
    "LEG_JOINT_TYPE": 2,
    "ARM_JOINT_TYPE": 2,
    "TAIL_JOINT_TYPE": 1,
    "HAS_KNEE": 0,
    "HAS_ELBOW": 0,
    "HEAD_JOINTED": 1,
    "LEG_IS_CIRCLE": 1,
    "FOOT_IS_CIRCLE": 1,
    "LEG_HAS_FOOT": 1,
    "HAS_FOOT": 1,
    "FOOT_IS_HOOF": 0,
    "FOOT_SIZE": 0,
    "FOOT_THICKNESS": 7,
    "FOOT_BACKWARDS": 1,
    "LEG_COUNT": 1,
    "LEG_LENGTH": 120,
    "LEG_STRETCH": 14,
    "LEG_STRETCH2": 14,
    "LEG_SKEW": 24,
    "LEG_STRENGTH": 120,
    "LEG_THRUST_BACK": 2,
    "ARM_HAS_HAND": 1,
    "HAS_HAND": 1,
    "ARM_LENGTH": 120,
    "ARM_STRENGTH": 120,
    "ARM_STRETCH": 14,
    "ARM_STRETCH2": 14,
    "ARM_SKEW": 20,
    "ARM_FLEXIBILITY": 15,
    "NECK_LENGTH": 90,
    "NECK_GIRAFFE": 120,
    "NECK_FLEXIBILITY": 15,
    "NECK_STIFF": 0,
    "TAIL_EXISTS": 1,
    "TAIL_SIZE": 140,
    "TAIL_SHORT": 35,
    "TAIL_ASPECT": 50,
    "TAIL_ANGLE": 60,
    "TAIL_STIFF": 1,
    "TAIL_SPEED": 200,
    "TAIL_FLEXIBILITY": 15,
    "TAIL_SEGMENTS": 5,
    "TAIL_WAG": 1,
    "L_LEG_SIGNAL": 2,
    "L_ARM_SIGNAL": 1,
    "L_TAIL_SIGNAL": 4,
    "L_NECK_SIGNAL": 3,
    "L_LEG_FTOB_REACT": 3,
    "L_LEG_FTOB_EVENT": 4,
    "L_LEG_BTOF_REACT": 3,
    "L_LEG_BTOF_EVENT": 4,
    "L_ARM_FTOB_REACT": 3,
    "L_ARM_FTOB_EVENT": 4,
    "L_ARM_BTOF_REACT": 3,
    "L_ARM_BTOF_EVENT": 4,
    "L_TAIL_FTOB_REACT": 3,
    "L_TAIL_FTOB_EVENT": 4,
    "L_TAIL_BTOF_REACT": 3,
    "L_TAIL_BTOF_EVENT": 4,
    "L_NECK_FTOB_REACT": 3,
    "L_NECK_FTOB_EVENT": 4,
    "L_NECK_BTOF_REACT": 3,
    "L_NECK_BTOF_EVENT": 4,
}

TINY_CAR_PRESET: Dict[str, int] = {
    **FAST_WHEELED_HORSE,
    "SIZE": 35,
    "GIANT_DWARF": 66,
    "SKINNY": 75,
    "ASPECT": 200,
    "GUT": 0,
    "DERRIERE": 0,
    "FOOT_SIZE": 0,
    "FOOT_THICKNESS": 7,
    "HEAD_SIZE": 75,
    "TAIL_SIZE": 80,
}

NO_GLITCH_INTACT: Dict[str, int] = {
    **CORE_RACE,
    "QUADRUPED": 1,
    "BIPED": 0,
    "LEG_HAS_FOOT": 1,
    "HAS_FOOT": 1,
    "LEG_IS_CIRCLE": 0,
    "FOOT_IS_CIRCLE": 0,
    "LEG_STRETCH": 0,
    "LEG_STRETCH2": 0,
    "LEG_SKEW": 0,
    "LEG_AND_ARM_LIMP": 0,
    "STIFF_JOINTS": 0,
    "NECK_STIFF": 1,
    "BREAK_FORCE": 0,
    "TAIL_EXISTS": 1,
    "TAIL_WAG": 0,
}

RACING_TARGETS = {
    "None / normal genes": {},
    "Clean speed horse": CLEAN_SPEED_HORSE,
    "Fast wheeled horse": FAST_WHEELED_HORSE,
    "Tank / multi-wheel": TANK_MULTI_WHEEL,
    "Oval wheel roller": OVAL_WHEEL_ROLLER,
    "Living Segway": LIVING_SEGWAY,
    "Tail launcher": TAIL_LAUNCHER,
    "Exploding finisher": EXPLODING_FINISHER,
    "Tiny car": TINY_CAR_PRESET,
    "No-glitch intact racer": NO_GLITCH_INTACT,
}

HELIX_TARGETS = {
    "Unchanged": {},
    "Speed core": CORE_RACE,
    "Wheel/contact": FAST_WHEELED_HORSE,
    "Oval roller": OVAL_WHEEL_ROLLER,
    "Tank/multi-wheel": TANK_MULTI_WHEEL,
    "Tail launcher": TAIL_LAUNCHER,
    "Exploding finisher": EXPLODING_FINISHER,
    "Tiny car": TINY_CAR_PRESET,
    "Intact/stable": NO_GLITCH_INTACT,
}

RACING_ALIAS = {
    "Clean racer": "Clean speed horse",
    "Car mode": "Fast wheeled horse",
    "Roll mode": "Oval wheel roller",
    "Legless mode": "Tail launcher",
    "Tail power mode": "Tail launcher",
    "Exploder": "Exploding finisher",
    "Part-launch finisher": "Exploding finisher",
    "Tiny horse mode": "Tiny car",
    "Launch-angle tire racer": "Living Segway",
}
HELIX_ALIAS = {
    "Clean racer": "Speed core",
    "Car/wheels": "Wheel/contact",
    "Roll": "Oval roller",
    "Legless": "Tail launcher",
    "Tail power": "Tail launcher",
    "Exploding": "Exploding finisher",
    "Tiny horse": "Tiny car",
    "Stable/no-glitch": "Intact/stable",
}

BASE_BACKUP_NAME = "genes.xml.caseoh90000_original"
REPORT_NAME = "sim_gene_lab_report.json"

CASEOH_OVERRIDE_NOTE = "Easter Egg."


def force_caseoh_override_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of settings with caseOh's override behavior made explicit.

    Easter Egg is intentionally not stackable with Gene Lab or search profiles.
    """
    out = dict(settings or {})
    out["caseoh_mode"] = bool(out.get("caseoh_mode", False))
    if out["caseoh_mode"]:
        defaults = default_gene_lab_settings()
        out["gene_lab_enabled"] = False
        out["species_profile"] = defaults["species_profile"]
        out["racing_preset"] = defaults["racing_preset"]
        out["helix_presets"] = dict(defaults["helix_presets"])
    return out


def gene_paths(branch: Path) -> Tuple[Path, Path]:
    branch = Path(branch)
    return branch / "data" / "genes.xml", branch / "data" / BASE_BACKUP_NAME


def ensure_base_backup(branch: Path) -> Path:
    genes, backup = gene_paths(branch)
    if not genes.exists():
        raise FileNotFoundError(genes)
    if not backup.exists():
        # Prefer older pristine backups if they already exist from previous tools.
        for candidate in [branch / "data" / "genes.xml.caseoh_original", branch / "data" / "genes.xml.gene_lab_original"]:
            if candidate.exists():
                shutil.copy2(candidate, backup)
                break
        else:
            shutil.copy2(genes, backup)
    return backup


def restore_gene_xml(branch: Path) -> Dict[str, Any]:
    genes, backup = gene_paths(branch)
    if backup.exists():
        shutil.copy2(backup, genes)
        report = Path(branch) / REPORT_NAME
        if report.exists():
            report.unlink()
        return {"restored": True, "backup": str(backup)}
    return {"restored": False, "reason": "no backup yet"}


def _set_all_alleles(elem: ET.Element, value: int, source: str, changed: List[Dict[str, Any]]) -> None:
    old = [elem.attrib.get(f"g{i}") for i in range(4)]
    for i in range(4):
        elem.attrib[f"g{i}"] = str(int(value))
    elem.attrib["caseoh90000_profile"] = source
    changed.append({"gene": elem.attrib.get("name", ""), "value": int(value), "source": source, "old": old})


def _apply_targets(by_name: Dict[str, ET.Element], targets: Dict[str, int], source: str, changed: List[Dict[str, Any]], allowed: set[str] | None = None) -> None:
    for gene, value in targets.items():
        if allowed is not None and gene not in allowed:
            continue
        elem = by_name.get(gene)
        if elem is None:
            continue
        _set_all_alleles(elem, int(value), source, changed)


def _caseoh_target_value(elem: ET.Element, spec: Dict[str, Any]) -> int:
    vals = [int(elem.attrib.get(f"g{i}", "0")) for i in range(4)]
    mode = str(spec.get("mode", "explicit")).lower()
    if mode == "min":
        return min(vals)
    if mode == "max":
        return max(vals)
    return int(spec.get("value", vals[0]))


def _apply_caseoh(by_name: Dict[str, ET.Element], changed: List[Dict[str, Any]]) -> None:
    for gene, spec in CASEOH_TARGETS.items():
        elem = by_name.get(gene)
        if elem is None:
            continue
        _set_all_alleles(elem, _caseoh_target_value(elem, spec), "Easter Egg", changed)


def helix_allowed_genes(gene_names: List[str], helix: str) -> set[str]:
    try:
        return set(HELIX_GENE_NAMES[int(helix)])
    except Exception:
        return set()


def default_gene_lab_settings() -> Dict[str, Any]:
    return {
        "gene_lab_enabled": False,
        "species_profile": "Any / no species lock",
        "racing_preset": "None / normal genes",
        "helix_presets": {f"{i:02d}": "Unchanged" for i in range(20)},
    }


def normalize_gene_lab_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    out = default_gene_lab_settings()
    out.update(settings or {})
    out["gene_lab_enabled"] = bool(out.get("gene_lab_enabled", False))
    if out.get("species_profile") not in SPECIES_PROFILES:
        out["species_profile"] = "Any / no species lock"
    out["racing_preset"] = RACING_ALIAS.get(out.get("racing_preset"), out.get("racing_preset"))
    if out.get("racing_preset") not in RACING_PRESETS:
        out["racing_preset"] = "None / normal genes"
    hp = dict(default_gene_lab_settings()["helix_presets"])
    hp.update(out.get("helix_presets") or {})
    for k, v in list(hp.items()):
        if k not in HELIX_RANGES:
            hp.pop(k, None)
        else:
            hp[k] = HELIX_ALIAS.get(v, v)
            if hp[k] not in HELIX_PRESETS:
                hp[k] = "Unchanged"
    out["helix_presets"] = hp
    return out


def apply_gene_stack(branch: Path, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Restore original genes.xml, then apply the active expression profile.

    v1.4 behavior: Easter Egg is a full override. It does not stack with the Gene Lab.
    """
    branch = Path(branch)
    genes, backup = gene_paths(branch)
    ensure_base_backup(branch)
    settings = force_caseoh_override_settings(settings)
    gl = normalize_gene_lab_settings(settings)
    tree = ET.parse(backup)
    root = tree.getroot()
    elems = root.findall("gene")
    gene_names = [e.attrib.get("name", "") for e in elems]
    by_name = {name: elem for name, elem in zip(gene_names, elems) if name}
    changed: List[Dict[str, Any]] = []

    if gl["gene_lab_enabled"]:
        species = gl["species_profile"]
        racing = gl["racing_preset"]
        _apply_targets(by_name, SPECIES_TARGETS.get(species, {}), f"species: {species}", changed)
        _apply_targets(by_name, RACING_TARGETS.get(racing, {}), f"racing: {racing}", changed)
        for helix, preset in sorted(gl["helix_presets"].items()):
            if preset == "Unchanged":
                continue
            allowed = helix_allowed_genes(gene_names, helix)
            _apply_targets(by_name, HELIX_TARGETS.get(preset, {}), f"helix {helix}: {preset}", changed, allowed=allowed)

        # Anything-goes exploding finishers must win over intact/no-glitch safety
        # profiles. Users asked for this preset to override protections that would
        # otherwise prevent part-launch/explosion finishes. Re-apply it last when
        # it is the global racing archetype.
        if gl["racing_preset"] == "Exploding finisher":
            _apply_targets(by_name, EXPLODING_FINISHER, "racing: Exploding finisher final override", changed)

    if bool(settings.get("caseoh_mode", False)):
        _apply_caseoh(by_name, changed)

    try:
        ET.indent(tree, space="    ")
    except Exception:
        pass
    tree.write(genes, encoding="unicode", short_empty_elements=True)

    if bool(settings.get("caseoh_mode", False)):
        report = {
            "version": "HorseyGameCaseOhMod v2 SIM Gene Lab",
            "enabled": False,
            "easter_egg_active": True,
            "changed_gene_count": len({c["gene"] for c in changed}),
            "changes": [],
        }
    else:
        report = {
            "version": "HorseyGameCaseOhMod v2 SIM Gene Lab",
            "enabled": bool(gl["gene_lab_enabled"]),
            "easter_egg_active": False,
            "species_profile": gl["species_profile"],
            "racing_preset": gl["racing_preset"],
            "helix_presets": gl["helix_presets"],
            "changed_gene_count": len({c["gene"] for c in changed}),
            "changes": changed,
        }
    (branch / REPORT_NAME).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def profile_status(branch: Path) -> Dict[str, Any]:
    genes, backup = gene_paths(Path(branch))
    report = Path(branch) / REPORT_NAME
    return {
        "genes_xml_exists": genes.exists(),
        "base_backup_exists": backup.exists(),
        "report_exists": report.exists(),
        "species_profiles": SPECIES_PROFILES,
        "racing_presets": RACING_PRESETS,
        "helix_presets": HELIX_PRESETS,
    }
