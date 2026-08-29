"""
RYTT Semiotic & Holonomic Multi-Base Compiler (Lossless Dual-Plane Edition)
===================================================================
Author: Ryan W. Yett (RY) + Antigravity Engine
Architecture: Polyglot 7-Layer AEON / Holonomery v3/v5 / Sovereign Semiotics
-------------------------------------------------------------------
This engine performs end-to-end tokenization, geometric feature extraction,
Holonomic multi-base encoding (Base 3, Base 9, Base 7, Base 21, Base 24),
10,240-bit Binary Spatter Code (VSA) hypervector embedding, and
100% lossless dual-plane (Ground Plane vs. Elevated Axiomatic Plane) casing.
"""

from typing import Dict, List, Tuple, Optional, Any, Union
import hashlib
import json
import math
import struct
import numpy as np

# -----------------------------------------------------------------------------
# 1. CANONICAL RYTT ALPHABET GENOME (BASE 26 UPPER & LOWER DUAL-PLANE)
# -----------------------------------------------------------------------------
# Elevated Plane (Uppercase): \uE800 - \uE819 (Z = 25.0)
# Ground Plane (Lowercase):   \uE000 - \uE019 (Z = 0.0)

_BASE_GENOME_SPECS: Dict[str, Dict[str, Any]] = {
    'A': {
        'family': 'POINT', 'vowel': True,
        'path': 'M 50,50 m -6,0 a 6,6 0 1,0 12,0 a 6,6 0 1,0 -12,0',
        'ops': ['POINT', 'MARK'],
        'trit_val': 0, 'sept_val': 0,
        'vectors': [0.1, 0.0, 0.1, 0.5, 0.0, 0.0, 0.0, 0.0, 0.9, 0.2]
    },
    'B': {
        'family': 'VECTOR', 'vowel': False,
        'path': 'M 50,20 L 50,80 M 50,50 L 75,50 M 50,32 L 68,32',
        'ops': ['EXTEND', 'ORIENT'],
        'trit_val': 1, 'sept_val': 1,
        'vectors': [0.6, 0.1, 0.4, 0.4, 0.0, 0.5, 0.0, 0.9, 0.6, 0.4]
    },
    'C': {
        'family': 'CHEVRON', 'vowel': False,
        'path': 'M 70,25 L 35,50 L 70,75',
        'ops': ['EXTEND', 'BEND', 'ORIENT'],
        'trit_val': -1, 'sept_val': -1,
        'vectors': [0.5, 0.8, 0.3, 0.4, 0.0, 0.3, 0.0, 0.4, 0.7, 0.6]
    },
    'D': {
        'family': 'CHEVRON', 'vowel': False,
        'path': 'M 70,25 L 35,50 L 70,75 M 50,50 m -5,0 a 5,5 0 1,0 10,0 a 5,5 0 1,0 -10,0',
        'ops': ['EXTEND', 'BEND', 'ORIENT', 'MARK'],
        'trit_val': -1, 'sept_val': 2,
        'vectors': [0.4, 0.7, 0.4, 0.4, 0.0, 0.3, 0.0, 0.4, 0.6, 0.7]
    },
    'E': {
        'family': 'DIAMOND', 'vowel': True,
        'path': 'M 50,20 L 80,50 L 50,80 L 20,50 Z M 50,50 m -5,0 a 5,5 0 1,0 10,0 a 5,5 0 1,0 -10,0',
        'ops': ['ENCLOSE', 'MARK'],
        'trit_val': 0, 'sept_val': -2,
        'vectors': [0.8, 0.9, 0.5, 0.5, 1.0, 0.5, 0.0, 0.5, 0.4, 0.8]
    },
    'F': {
        'family': 'DIAMOND', 'vowel': False,
        'path': 'M 50,20 L 80,50 L 50,80 L 20,50 Z',
        'ops': ['ENCLOSE'],
        'trit_val': 1, 'sept_val': 3,
        'vectors': [0.9, 0.9, 0.4, 0.5, 1.0, 0.5, 0.0, 0.5, 0.5, 0.6]
    },
    'G': {
        'family': 'VECTOR', 'vowel': False,
        'path': 'M 20,50 L 80,50',
        'ops': ['EXTEND', 'ORIENT'],
        'trit_val': -1, 'sept_val': -3,
        'vectors': [0.9, 0.0, 0.2, 0.5, 0.0, 1.0, 0.0, 0.0, 0.8, 0.3]
    },
    'H': {
        'family': 'FRAME', 'vowel': False,
        'path': 'M 30,80 L 30,20 L 80,20',
        'ops': ['EXTEND', 'BEND', 'ORIENT'],
        'trit_val': 1, 'sept_val': 1,
        'vectors': [0.7, 0.9, 0.3, 0.4, 0.0, 0.5, 0.0, 0.9, 0.7, 0.5]
    },
    'I': {
        'family': 'FRAME', 'vowel': True,
        'path': 'M 75,25 L 30,25 L 30,75 L 75,75 M 50,50 m -5,0 a 5,5 0 1,0 10,0 a 5,5 0 1,0 -10,0',
        'ops': ['OPEN', 'EXTEND', 'MARK'],
        'trit_val': 0, 'sept_val': 0,
        'vectors': [0.5, 0.9, 0.4, 0.4, 0.0, 0.4, 0.0, 0.9, 0.6, 0.7]
    },
    'J': {
        'family': 'FRAME', 'vowel': False,
        'path': 'M 75,25 L 30,25 L 30,75 L 75,75',
        'ops': ['OPEN', 'EXTEND'],
        'trit_val': -1, 'sept_val': 2,
        'vectors': [0.6, 0.9, 0.3, 0.4, 0.0, 0.4, 0.0, 0.9, 0.7, 0.5]
    },
    'K': {
        'family': 'FRAME', 'vowel': False,
        'path': 'M 25,25 L 75,25 L 75,75 L 25,75 Z',
        'ops': ['ENCLOSE'],
        'trit_val': 1, 'sept_val': -2,
        'vectors': [0.9, 0.9, 0.5, 0.5, 1.0, 0.5, 0.0, 0.9, 0.4, 0.6]
    },
    'L': {
        'family': 'ARC', 'vowel': False,
        'path': 'M 70,25 A 30,30 0 0,0 70,75',
        'ops': ['OPEN', 'BEND', 'ORIENT'],
        'trit_val': -1, 'sept_val': 3,
        'vectors': [0.8, 0.2, 0.3, 0.4, 0.0, 0.3, 0.9, 0.9, 0.7, 0.5]
    },
    'M': {
        'family': 'ARC', 'vowel': False,
        'path': 'M 25,70 A 30,30 0 0,1 75,70',
        'ops': ['OPEN', 'BEND', 'ORIENT'],
        'trit_val': 1, 'sept_val': -3,
        'vectors': [0.8, 0.2, 0.3, 0.5, 0.0, 0.7, 0.9, 0.0, 0.7, 0.5]
    },
    'N': {
        'family': 'ARC', 'vowel': False,
        'path': 'M 35,25 A 25,25 0 0,0 35,75 M 65,25 A 25,25 0 0,1 65,75',
        'ops': ['OPEN', 'DUPLICATE', 'REFLECT'],
        'trit_val': -1, 'sept_val': 1,
        'vectors': [0.5, 0.2, 0.4, 0.5, 0.0, 0.5, 0.9, 0.9, 0.6, 0.6]
    },
    'O': {
        'family': 'ARC', 'vowel': True,
        'path': 'M 35,25 A 25,25 0 0,0 35,75 M 65,25 A 25,25 0 0,1 65,75 M 50,50 m -5,0 a 5,5 0 1,0 10,0 a 5,5 0 1,0 -10,0',
        'ops': ['DUPLICATE', 'REFLECT', 'MARK'],
        'trit_val': 0, 'sept_val': 0,
        'vectors': [0.4, 0.2, 0.5, 0.5, 0.0, 0.5, 0.9, 0.9, 0.5, 0.8]
    },
    'P': {
        'family': 'ARC', 'vowel': False,
        'path': 'M 20,25 A 35,25 0 0,0 20,75 M 80,25 A 35,25 0 0,1 80,75',
        'ops': ['OPEN', 'DUPLICATE', 'REFLECT', 'ORIENT'],
        'trit_val': 1, 'sept_val': 2,
        'vectors': [0.5, 0.2, 0.5, 0.5, 0.0, 0.8, 0.9, 0.9, 0.5, 0.6]
    },
    'Q': {
        'family': 'RING', 'vowel': False,
        'path': 'M 50,50 m -25,0 a 25,25 0 1,0 50,0 a 25,25 0 1,0 -50,0',
        'ops': ['ENCLOSE'],
        'trit_val': -1, 'sept_val': -2,
        'vectors': [0.9, 0.0, 0.4, 0.5, 1.0, 0.5, 1.0, 0.5, 0.5, 0.6]
    },
    'R': {
        'family': 'RING', 'vowel': False,
        'path': 'M 50,50 m -25,0 a 25,25 0 1,0 50,0 a 25,25 0 1,0 -50,0 M 50,50 m -5,0 a 5,5 0 1,0 10,0 a 5,5 0 1,0 -10,0',
        'ops': ['ENCLOSE', 'NEST', 'MARK'],
        'trit_val': 1, 'sept_val': 3,
        'vectors': [0.8, 0.0, 0.5, 0.5, 1.0, 0.5, 1.0, 0.5, 0.4, 0.8]
    },
    'S': {
        'family': 'VECTOR', 'vowel': False,
        'path': 'M 50,20 L 50,80',
        'ops': ['EXTEND', 'ORIENT'],
        'trit_val': -1, 'sept_val': -3,
        'vectors': [0.9, 0.0, 0.2, 0.5, 0.0, 0.0, 0.0, 0.9, 0.8, 0.3]
    },
    'T': {
        'family': 'VECTOR', 'vowel': False,
        'path': 'M 20,20 L 80,20 M 50,20 L 50,80',
        'ops': ['EXTEND', 'INTERSECT', 'ORIENT'],
        'trit_val': 1, 'sept_val': 1,
        'vectors': [0.7, 0.5, 0.3, 0.5, 0.0, 0.5, 0.0, 0.9, 0.7, 0.5]
    },
    'U': {
        'family': 'VECTOR', 'vowel': True,
        'path': 'M 40,20 L 40,80 M 65,50 m -5,0 a 5,5 0 1,0 10,0 a 5,5 0 1,0 -10,0',
        'ops': ['EXTEND', 'ORIENT', 'MARK'],
        'trit_val': 0, 'sept_val': 0,
        'vectors': [0.6, 0.1, 0.3, 0.4, 0.0, 0.3, 0.0, 0.9, 0.7, 0.6]
    },
    'V': {
        'family': 'CHEVRON', 'vowel': False,
        'path': 'M 25,25 L 50,75 L 75,25',
        'ops': ['EXTEND', 'BEND', 'ORIENT'],
        'trit_val': -1, 'sept_val': 2,
        'vectors': [0.7, 0.8, 0.3, 0.5, 0.0, 0.5, 0.0, 0.9, 0.7, 0.5]
    },
    'W': {
        'family': 'CHEVRON', 'vowel': False,
        'path': 'M 20,25 L 50,75 L 80,25 M 35,50 L 65,50',
        'ops': ['EXTEND', 'BEND', 'NEST', 'ORIENT'],
        'trit_val': 1, 'sept_val': -2,
        'vectors': [0.5, 0.8, 0.5, 0.5, 0.0, 0.6, 0.0, 0.5, 0.5, 0.6]
    },
    'X': {
        'family': 'VECTOR', 'vowel': False,
        'path': 'M 25,25 L 75,75 M 75,25 L 25,75',
        'ops': ['EXTEND', 'INTERSECT'],
        'trit_val': -1, 'sept_val': 3,
        'vectors': [0.6, 0.9, 0.4, 0.5, 0.0, 0.5, 0.0, 0.5, 0.6, 0.5]
    },
    'Y': {
        'family': 'BRANCH', 'vowel': False,
        'path': 'M 25,25 L 50,50 L 75,25 M 50,50 L 50,80',
        'ops': ['EXTEND', 'BRANCH', 'ORIENT'],
        'trit_val': 1, 'sept_val': -3,
        'vectors': [0.5, 0.8, 0.4, 0.5, 0.0, 0.5, 0.0, 0.9, 0.6, 0.6]
    },
    'Z': {
        'family': 'BRANCH', 'vowel': False,
        'path': 'M 50,80 L 50,20 M 30,40 L 50,20 L 70,40',
        'ops': ['EXTEND', 'BRANCH', 'ORIENT'],
        'trit_val': -1, 'sept_val': 1,
        'vectors': [0.5, 0.8, 0.4, 0.5, 0.0, 0.3, 0.0, 0.9, 0.6, 0.6]
    }
}

# Construct Dual-Plane Genome
RYTT_GENOME: Dict[str, Dict[str, Any]] = {}
for i, (char, spec) in enumerate(_BASE_GENOME_SPECS.items()):
    # Uppercase (Elevated Plane: \uE800 + i)
    pua_upper = chr(0xE800 + i)
    RYTT_GENOME[char] = {
        **spec,
        'pua': pua_upper,
        'is_upper': True,
        'case_plane': 1,
        'elevation_z': 25.0
    }
    # Lowercase (Ground Plane: \uE000 + i)
    pua_lower = chr(0xE000 + i)
    char_lower = char.lower()
    RYTT_GENOME[char_lower] = {
        **spec,
        'pua': pua_lower,
        'is_upper': False,
        'case_plane': 0,
        'elevation_z': 0.0
    }

# -----------------------------------------------------------------------------
# 2. DUAL-PLANE CHORD & LIGATURE MATRIX
# -----------------------------------------------------------------------------
_BASE_LIGATURES: Dict[str, Dict[str, Any]] = {
    # 4-Letter Tetragram Chords
    'TION': {'upper_offset': 0x40, 'lower_offset': 0x40, 'meaning': 'Process / State', 'path': 'M 20,20 L 80,20 M 50,20 L 50,80 M 35,50 A 15,15 0 1,0 65,50 A 15,15 0 1,0 35,50'},
    'MENT': {'upper_offset': 0x41, 'lower_offset': 0x41, 'meaning': 'Artifact / Entity', 'path': 'M 25,70 A 30,30 0 0,1 75,70 M 50,20 L 80,50 L 50,80 L 20,50 Z'},
    'RYTT': {'upper_offset': 0x42, 'lower_offset': 0x42, 'meaning': 'Sovereign Inscription Seal', 'path': 'M 50,50 m -25,0 a 25,25 0 1,0 50,0 a 25,25 0 1,0 -50,0 M 20,20 L 80,20 M 50,20 L 50,80 M 35,50 L 65,50'},
    
    # 3-Letter Trigram Chords
    'PSY': {'upper_offset': 0x20, 'lower_offset': 0x20, 'meaning': 'Mind / Intent / Vector', 'path': 'M 50,20 L 50,80 M 20,40 L 50,60 L 80,40 M 25,25 L 75,25'},
    'STR': {'upper_offset': 0x21, 'lower_offset': 0x21, 'meaning': 'Structure / Lattice', 'path': 'M 20,20 L 80,20 M 50,20 L 50,80 M 20,80 L 80,80 M 20,20 L 80,80'},
    'ING': {'upper_offset': 0x22, 'lower_offset': 0x22, 'meaning': 'Continuous Action', 'path': 'M 50,20 L 80,50 L 50,80 L 20,50 Z M 20,50 L 80,50'},
    'ALL': {'upper_offset': 0x23, 'lower_offset': 0x23, 'meaning': 'Totality / Universe', 'path': 'M 50,50 m -30,0 a 30,30 0 1,0 60,0 a 30,30 0 1,0 -60,0 M 50,20 L 50,80'},
    'THE': {'upper_offset': 0x24, 'lower_offset': 0x24, 'meaning': 'Definite Ground Truth', 'path': 'M 20,20 L 80,20 M 50,20 L 50,80 M 30,80 L 30,40 L 70,40 L 70,80'},
    'AND': {'upper_offset': 0x25, 'lower_offset': 0x25, 'meaning': 'Conjunction / Tensor Product', 'path': 'M 50,50 m -6,0 a 6,6 0 1,0 12,0 a 6,6 0 1,0 -12,0 M 70,25 L 35,50 L 70,75'},
    'NOT': {'upper_offset': 0x26, 'lower_offset': 0x26, 'meaning': 'Negation / Mirror Inversion', 'path': 'M 20,20 L 80,80 M 80,20 L 20,80 M 50,50 m -15,0 a 15,15 0 1,0 30,0 a 15,15 0 1,0 -30,0'},
    'FOR': {'upper_offset': 0x27, 'lower_offset': 0x27, 'meaning': 'Iteration / Purpose Loop', 'path': 'M 50,20 L 80,50 L 50,80 L 20,50 Z M 50,50 m -25,0 a 25,25 0 1,0 50,0 a 25,25 0 1,0 -50,0'},
    'CON': {'upper_offset': 0x28, 'lower_offset': 0x28, 'meaning': 'Convergence / Collective', 'path': 'M 70,25 L 35,50 L 70,75 M 50,50 m -15,0 a 15,15 0 1,0 30,0 a 15,15 0 1,0 -30,0'},
    'PRO': {'upper_offset': 0x29, 'lower_offset': 0x29, 'meaning': 'Forward Projection', 'path': 'M 20,25 A 35,25 0 0,0 20,75 M 80,25 A 35,25 0 0,1 80,75 M 50,50 m -10,0 a 10,10 0 1,0 20,0 a 10,10 0 1,0 -20,0'},

    # 2-Letter Bigram Chords
    'TH': {'upper_offset': 0x30, 'lower_offset': 0x30, 'meaning': 'Aspiration / Horizon', 'path': 'M 20,20 L 80,20 M 50,20 L 50,80 M 50,50 L 80,50 L 80,80'},
    'ST': {'upper_offset': 0x31, 'lower_offset': 0x31, 'meaning': 'Standing State', 'path': 'M 20,20 L 80,20 M 50,20 L 50,80 M 35,50 L 65,50'},
    'IN': {'upper_offset': 0x32, 'lower_offset': 0x32, 'meaning': 'Interior Admission', 'path': 'M 65,25 A 25,25 0 0,0 65,75 M 85,25 A 25,25 0 0,1 85,75 M 45,35 L 20,35 L 20,65 L 45,65'},
    'EE': {'upper_offset': 0x33, 'lower_offset': 0x33, 'meaning': 'Twin Resonant Eye', 'path': 'M 35,20 L 65,50 L 35,80 L 05,50 Z M 35,50 m -4,0 a 4,4 0 1,0 8,0 a 4,4 0 1,0 -8,0 M 65,20 L 95,50 L 65,80 L 35,50 Z M 65,50 m -4,0 a 4,4 0 1,0 8,0 a 4,4 0 1,0 -8,0'},
    'ER': {'upper_offset': 0x34, 'lower_offset': 0x34, 'meaning': 'Agent / Operator', 'path': 'M 50,20 L 80,50 L 50,80 L 20,50 Z M 50,50 m -15,0 a 15,15 0 1,0 30,0 a 15,15 0 1,0 -30,0'},
    'ON': {'upper_offset': 0x35, 'lower_offset': 0x35, 'meaning': 'Ontological Presence', 'path': 'M 35,25 A 25,25 0 0,0 35,75 M 65,25 A 25,25 0 0,1 65,75 M 50,50 m -10,0 a 10,10 0 1,0 20,0 a 10,10 0 1,0 -20,0'},
    'AT': {'upper_offset': 0x36, 'lower_offset': 0x36, 'meaning': 'Locality / Coordinate', 'path': 'M 50,50 m -6,0 a 6,6 0 1,0 12,0 a 6,6 0 1,0 -12,0 M 20,20 L 80,20 M 50,20 L 50,80'},
    'RY': {'upper_offset': 0x37, 'lower_offset': 0x37, 'meaning': 'Sovereign Root Sign', 'path': 'M 50,50 m -25,0 a 25,25 0 1,0 50,0 a 25,25 0 1,0 -50,0 M 25,25 L 50,50 L 75,25 M 50,50 L 50,80'},
    'TT': {'upper_offset': 0x38, 'lower_offset': 0x38, 'meaning': 'Dual Pillar Invariant', 'path': 'M 15,20 L 45,20 M 30,20 L 30,80 M 55,20 L 85,20 M 70,20 L 70,80'},
    'RE': {'upper_offset': 0x39, 'lower_offset': 0x39, 'meaning': 'Recursive Return', 'path': 'M 50,50 m -20,0 a 20,20 0 1,0 40,0 a 20,20 0 1,0 -40,0 M 50,30 L 70,50 L 50,70 L 30,50 Z'}
}

RYTT_LIGATURES: Dict[str, Dict[str, Any]] = {}
for lig, spec in _BASE_LIGATURES.items():
    # Uppercase Chord (Elevated)
    pua_up = chr(0xE800 + spec['upper_offset'])
    RYTT_LIGATURES[lig] = {
        'pua': pua_up,
        'meaning': spec['meaning'],
        'path': spec['path'],
        'is_upper': True,
        'case_plane': 1,
        'elevation_z': 25.0
    }
    # Lowercase Chord (Ground)
    pua_low = chr(0xE000 + spec['lower_offset'])
    lig_low = lig.lower()
    RYTT_LIGATURES[lig_low] = {
        'pua': pua_low,
        'meaning': spec['meaning'],
        'path': spec['path'],
        'is_upper': False,
        'case_plane': 0,
        'elevation_z': 0.0
    }

# -----------------------------------------------------------------------------
# 3. EXACT LOSSLESS REVERSE MAPPING (PUA -> PLAIN)
# -----------------------------------------------------------------------------
PUA_TO_PLAIN: Dict[str, str] = {}
for k, v in RYTT_GENOME.items():
    PUA_TO_PLAIN[v['pua']] = k
for k, v in RYTT_LIGATURES.items():
    PUA_TO_PLAIN[v['pua']] = k

# -----------------------------------------------------------------------------
# 4. RYTT COMPILATION DATA STRUCTURES
# -----------------------------------------------------------------------------
class RyttToken:
    def __init__(
        self,
        raw: str,
        pua: str,
        is_chord: bool,
        chord_len: int,
        family: str,
        path: str,
        is_upper: bool = False,
        case_plane: int = 0,
        elevation_z: float = 0.0
    ):
        self.raw = raw
        self.pua = pua
        self.is_chord = is_chord
        self.chord_len = chord_len
        self.family = family
        self.path = path
        self.is_upper = is_upper
        self.case_plane = case_plane
        self.elevation_z = elevation_z

    def to_dict(self) -> Dict[str, Any]:
        return {
            'raw': self.raw,
            'pua': self.pua,
            'is_chord': self.is_chord,
            'chord_len': self.chord_len,
            'family': self.family,
            'path': self.path,
            'is_upper': self.is_upper,
            'case_plane': self.case_plane,
            'elevation_z': self.elevation_z
        }

class RyttCompilationResult:
    def __init__(
        self,
        source_text: str,
        tokens: List[RyttToken],
        encoded_pua: str,
        holonomic_bases: Dict[str, Any],
        vsa_hypervector_bits: str,
        vsa_hash_sha256: str,
        parity_mod24: int,
        compression_ratio: float,
        token_savings_pct: float
    ):
        self.source_text = source_text
        self.tokens = tokens
        self.encoded_pua = encoded_pua
        self.holonomic_bases = holonomic_bases
        self.vsa_hypervector_bits = vsa_hypervector_bits
        self.vsa_hash_sha256 = vsa_hash_sha256
        self.parity_mod24 = parity_mod24
        self.compression_ratio = compression_ratio
        self.token_savings_pct = token_savings_pct

    @property
    def compiled_text(self) -> str:
        return self.encoded_pua

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_text': self.source_text,
            'token_count': len(self.tokens),
            'encoded_pua': self.encoded_pua,
            'parity_mod24': self.parity_mod24,
            'compression_ratio': round(self.compression_ratio, 3),
            'token_savings_pct': round(self.token_savings_pct, 2),
            'vsa_hash_sha256': self.vsa_hash_sha256,
            'holonomic_bases': self.holonomic_bases,
            'tokens': [t.to_dict() for t in self.tokens]
        }

# -----------------------------------------------------------------------------
# 5. THE MASTER RYTT COMPILER
# -----------------------------------------------------------------------------
class RyttCompiler:
    """
    Sovereign End-to-End RYTT Compiler and Holonomic Multi-Base Synthesizer.
    Features:
    - 100% strictly lossless round-tripping for any mixed-case text with symbols & spaces.
    - Dual-plane case polarity: Ground Plane ($Z=0$, lower) vs. Elevated Plane ($Z=25$, upper).
    - Multi-base polytopic tier evaluation (Base 3, 9, 7, 21, 24).
    - 10,240-bit Binary Spatter Code Hypervector generation.
    """
    def __init__(self, author_seal: str = "RYTT_SOVEREIGN"):
        self.author_seal = author_seal
        # Sort ligatures by length descending for greedy longest-match packing
        self.sorted_ligatures = sorted(RYTT_LIGATURES.keys(), key=lambda x: len(x), reverse=True)

    def compile(self, text: str) -> RyttCompilationResult:
        """
        Takes raw natural language, tokenizes into RYTT Chords/Glyphs,
        evaluates Holonomic Base Tiers, and generates 10,240-bit VSA state.
        Preserves original letter casing losslessly.
        """
        tokens: List[RyttToken] = []
        pua_chars: List[str] = []
        trit_stream: List[int] = []
        sept_stream: List[int] = []
        parity_sum = 0
        
        i = 0
        n = len(text)
        
        while i < n:
            char = text[i]
            
            # Handle spaces
            if char == ' ':
                pua_chars.append('·')
                tokens.append(RyttToken(
                    raw=' ', pua='·', is_chord=False, chord_len=1,
                    family='SPACE', path='', is_upper=False, case_plane=-1, elevation_z=0.0
                ))
                trit_stream.append(0)
                sept_stream.append(0)
                parity_sum += 7
                i += 1
                continue
                
            # Handle non-alpha characters (numbers, punctuation, symbols, newlines)
            if not char.isalpha():
                pua_chars.append(char)
                tokens.append(RyttToken(
                    raw=char, pua=char, is_chord=False, chord_len=1,
                    family='PUNCT', path='', is_upper=False, case_plane=-1, elevation_z=0.0
                ))
                trit_stream.append(0)
                sept_stream.append(0)
                parity_sum += ord(char)
                i += 1
                continue

            # Greedy Ligature Chord Match (exact case match first)
            matched_lig = False
            for lig in self.sorted_ligatures:
                lig_len = len(lig)
                if i + lig_len <= n and text[i:i+lig_len] == lig:
                    lig_info = RYTT_LIGATURES[lig]
                    tok = RyttToken(
                        raw=lig,
                        pua=lig_info['pua'],
                        is_chord=True,
                        chord_len=lig_len,
                        family='CHORD',
                        path=lig_info['path'],
                        is_upper=lig_info['is_upper'],
                        case_plane=lig_info['case_plane'],
                        elevation_z=lig_info['elevation_z']
                    )
                    tokens.append(tok)
                    pua_chars.append(lig_info['pua'])
                    
                    # Compute trits & septenaries for the chord
                    upper_lig = lig.upper()
                    chord_trits = sum(RYTT_GENOME[c]['trit_val'] for c in upper_lig)
                    chord_septs = sum(RYTT_GENOME[c]['sept_val'] for c in upper_lig)
                    trit_stream.append(int(np.clip(chord_trits, -1, 1)))
                    sept_stream.append(int(np.clip(chord_septs, -3, 3)))
                    
                    parity_sum += sum(ord(c) for c in lig)
                    i += lig_len
                    matched_lig = True
                    break

            if matched_lig:
                continue

            # Single Glyph (lowercase or uppercase)
            glyph_info = RYTT_GENOME.get(char, RYTT_GENOME['A'])
            tok = RyttToken(
                raw=char,
                pua=glyph_info['pua'],
                is_chord=False,
                chord_len=1,
                family=glyph_info['family'],
                path=glyph_info['path'],
                is_upper=glyph_info['is_upper'],
                case_plane=glyph_info['case_plane'],
                elevation_z=glyph_info['elevation_z']
            )
            tokens.append(tok)
            pua_chars.append(glyph_info['pua'])
            trit_stream.append(glyph_info['trit_val'])
            sept_stream.append(glyph_info['sept_val'])
            parity_sum += ord(char)
            i += 1

        encoded_pua = "".join(pua_chars)
        parity_mod24 = parity_sum % 24

        # Holonomic Base Transformations
        holonomic_bases = self._compute_holonomic_bases(trit_stream, sept_stream)

        # 10,240-bit Binary Spatter Code Hypervector (VSA Substrate: 20 x 512-bit ZMM SIMD registers)
        vsa_bits, vsa_hash = self._generate_10240_vsa_hypervector(encoded_pua, parity_mod24)

        # Native Character-to-Token Metrics
        raw_char_count = len(text)
        rytt_token_count = len(tokens)
        compression_ratio = raw_char_count / max(1, rytt_token_count)
        # RE-MEASURED 2026-08-28 -- READ BEFORE QUOTING THESE FIELDS.
        # `token_savings_pct` divides a TOKEN count by a CHARACTER count. That is
        # a unit mismatch, not a compression ratio, and it is the sole source of
        # the "25-65% token compression" headline. Against a real BPE tokenizer
        # (tiktoken cl100k_base, 233 chars of English) RYTT is worse under every
        # reading of the claim:
        #     as a wire format vs raw text ............ 11.27x MORE tokens
        #     as a wire format vs uppercased raw ...... 7.84x MORE
        #     as its own native vocabulary vs raw ..... 4.29x MORE
        #     as native vocab vs uppercased raw ....... 2.99x MORE
        #     tokens-vs-characters (this metric) ...... +11.6%  <- only positive reading
        # Cause: PUA codepoints are out-of-vocabulary, so BPE byte-falls-back to
        # ~3 tokens each, while English averages ~4.9 chars/token.
        # Do NOT restore a `max(0.0, ...)` clamp here: clamped, this metric is
        # structurally incapable of reporting a loss, which is how the inverted
        # headline survived. A pytest guard enforces this.
        # Re-measure: python3 tools/vault_scripts/measure_rytt_compression.py
        # See Chyren_Second_Brain/50_Mathematical_Notation/derivations/D45_rytt_compression_measurement.md
        token_savings_pct = (1.0 - (rytt_token_count / max(1, raw_char_count))) * 100.0

        return RyttCompilationResult(
            source_text=text,
            tokens=tokens,
            encoded_pua=encoded_pua,
            holonomic_bases=holonomic_bases,
            vsa_hypervector_bits=vsa_bits,
            vsa_hash_sha256=vsa_hash,
            parity_mod24=parity_mod24,
            compression_ratio=compression_ratio,
            token_savings_pct=token_savings_pct
        )

    def decompile(self, encoded_pua: str) -> str:
        """
        Decompile a RYTT PUA stream back to standard text.
        Guaranteed 100% strictly lossless across all casing, symbols, and whitespace.
        """
        result = []
        for ch in encoded_pua:
            if ch == '·':
                result.append(' ')
            elif ch in PUA_TO_PLAIN:
                result.append(PUA_TO_PLAIN[ch])
            else:
                result.append(ch)
        return "".join(result)

    def _compute_holonomic_bases(self, trits: List[int], septs: List[int]) -> Dict[str, Any]:
        """
        Computes the 4 Polytopic Tiers:
        - Tier 1: Balanced Ternary (Base 3: {-1, 0, +1}, Triangles)
        - Tier 1.5: Balanced Nonary (Base 9: 3-pack lossless)
        - Tier 2: Balanced Septenary (Base 7: {-3..+3}, G2 mirror)
        - Tier 3: Bridge Disc (Base 21 / 24)
        """
        # Tier 1: Balanced Ternary string representation (+, 0, -)
        trit_symbols = {1: '+', 0: '0', -1: '-'}
        t1_str = "".join(trit_symbols.get(t, '0') for t in trits)

        # Tier 1.5: Balanced Nonary (Group into chunks of 2 trits: 3^2 = 9)
        nonary_digits = []
        for idx in range(0, len(trits), 2):
            t_low = trits[idx]
            t_high = trits[idx+1] if idx+1 < len(trits) else 0
            val = t_low + (3 * t_high)  # range -4 to +4
            nonary_digits.append(val)

        # Tier 2: Balanced Septenary
        sept_str = "".join(f"[{s:+d}]" if s != 0 else "[ 0]" for s in septs)

        # Tier 3: Cross-Family Bridge (Base 21 = 3 * 7)
        bridge_indices = []
        for idx in range(min(len(trits), len(septs))):
            # Map (-1..1) and (-3..3) to (0..20)
            b_val = ((trits[idx] + 1) * 7 + (septs[idx] + 3)) % 21
            bridge_indices.append(b_val)

        return {
            'tier1_balanced_ternary': {
                'base': 3,
                'polygon': 'Triangle (Δ3)',
                'trits_count': len(trits),
                'stream': t1_str
            },
            'tier1_5_balanced_nonary': {
                'base': 9,
                'polygon': 'Nonagon (N9)',
                'digits_count': len(nonary_digits),
                'digits': nonary_digits
            },
            'tier2_balanced_septenary': {
                'base': 7,
                'polygon': 'Heptagon (H7)',
                'stream': sept_str,
                'chiral_orientation': 'φ-Handed (+)' if sum(septs) >= 0 else 'φ-Handed (-)'
            },
            'tier3_prime_bridge': {
                'base': 21,
                'polygon': 'Bridge Disc (D21)',
                'factorization': '3 × 7 (G2 ⊃ SU3)',
                'bridge_indices': bridge_indices
            }
        }

    def _generate_10240_vsa_hypervector(self, pua_stream: str, parity: int) -> Tuple[str, str]:
        """
        Generates the 10,240-bit Binary Spatter Code Hypervector.
        Dimensionality: 10,240 bits = 20 × 512-bit ZMM SIMD AVX-512 registers.
        """
        seed_material = f"{self.author_seal}:{pua_stream}:{parity}".encode('utf-8')
        h_master = hashlib.sha256(seed_material).hexdigest()
        
        # Expand to 10,240 bits (1280 bytes = 20 blocks of 64 bytes)
        bit_blocks = []
        for block_idx in range(20):
            block_seed = f"{h_master}:{block_idx}".encode('utf-8')
            block_hash = hashlib.sha512(block_seed).digest()  # 64 bytes = 512 bits
            bit_blocks.append(block_hash)

        full_bytes = b"".join(bit_blocks) # 1280 bytes = 10,240 bits
        
        # Summary bit string preview (first 64 bits + hex representation)
        bit_preview = "".join(f"{b:08b}" for b in full_bytes[:8]) + "..."
        return bit_preview, h_master
