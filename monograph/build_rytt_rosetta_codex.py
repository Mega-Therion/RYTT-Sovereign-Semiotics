import subprocess
import os
import re
import sys

# PGF / TikZ vector macro generator for each RYTT character
# Cyan for lowercase (Z=0), Gold for uppercase (Z=25)

def get_glyph_tikz(char, is_upper=False):
    c = char.upper()
    color = "gold" if is_upper else "cyan"
    
    # Precise vector path per character on a 0.28cm x 0.38cm box
    if c == 'A':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0.09,0.15) -- (0.18,-0.15); \draw[{color}, line width=0.5pt] (0.045,-0.02) -- (0.135,-0.02);}}"
    elif c == 'B':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15) -- (0.12,0.15) arc[start angle=90, end angle=-90, radius=0.075] -- (0,0) -- (0.14,0) arc[start angle=90, end angle=-90, radius=0.075] -- (0,-0.15);}}"
    elif c == 'C':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.16,0.12) arc[start angle=45, end angle=315, radius=0.15];}}"
    elif c == 'D':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15) -- (0.06,0.15) arc[start angle=90, end angle=-90, x radius=0.12, y radius=0.15] -- (0,-0.15);}}"
    elif c == 'E':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.15,0.15) -- (0,0.15) -- (0,-0.15) -- (0.15,-0.15); \draw[{color}, line width=0.6pt] (0,0) -- (0.11,0);}}"
    elif c == 'F':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.15,0.15) -- (0,0.15) -- (0,-0.15); \draw[{color}, line width=0.6pt] (0,0) -- (0.11,0);}}"
    elif c == 'G':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.16,0.12) arc[start angle=45, end angle=315, radius=0.15] -- (0.15, -0.02) -- (0.07, -0.02);}}"
    elif c == 'H':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15); \draw[{color}, line width=0.7pt] (0.15,-0.15) -- (0.15,0.15); \draw[{color}, line width=0.6pt] (0,0) -- (0.15,0);}}"
    elif c == 'I':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.075,-0.15) -- (0.075,0.15); \draw[{color}, line width=0.5pt] (0.01,0.15) -- (0.14,0.15); \draw[{color}, line width=0.5pt] (0.01,-0.15) -- (0.14,-0.15);}}"
    elif c == 'J':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.12,0.15) -- (0.12,-0.06) arc[start angle=0, end angle=-180, radius=0.07];}}"
    elif c == 'K':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15); \draw[{color}, line width=0.7pt] (0.15,0.15) -- (0,0) -- (0.15,-0.15);}}"
    elif c == 'L':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,0.15) -- (0,-0.15) -- (0.14,-0.15);}}"
    elif c == 'M':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15) -- (0.09,0) -- (0.18,0.15) -- (0.18,-0.15);}}"
    elif c == 'N':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15) -- (0.15,-0.15) -- (0.15,0.15);}}"
    elif c == 'O':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.08,0) circle [x radius=0.08, y radius=0.14];}}"
    elif c == 'P':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15) -- (0.10,0.15) arc[start angle=90, end angle=-90, radius=0.075] -- (0,0);}}"
    elif c == 'Q':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.08,0) circle [x radius=0.08, y radius=0.14]; \draw[{color}, line width=0.7pt] (0.10,-0.06) -- (0.17,-0.17);}}"
    elif c == 'R':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0,0.15) -- (0.10,0.15) arc[start angle=90, end angle=-90, radius=0.075] -- (0,0) -- (0.15,-0.15);}}"
    elif c == 'S':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0.14,0.10) arc[start angle=60, end angle=260, radius=0.07] to[out=0, in=180] (0.08,-0.01) arc[start angle=90, end angle=-120, radius=0.075];}}"
    elif c == 'T':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,0.15) -- (0.16,0.15); \draw[{color}, line width=0.7pt] (0.08,0.15) -- (0.08,-0.15);}}"
    elif c == 'U':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,0.15) -- (0,-0.05) arc[start angle=-180, end angle=0, radius=0.075] -- (0.15,0.15);}}"
    elif c == 'V':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,0.15) -- (0.08,-0.15) -- (0.16,0.15);}}"
    elif c == 'W':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,0.15) -- (0.04,-0.15) -- (0.09,0.05) -- (0.14,-0.15) -- (0.18,0.15);}}"
    elif c == 'X':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,-0.15) -- (0.16,0.15); \draw[{color}, line width=0.7pt] (0,0.15) -- (0.16,-0.15);}}"
    elif c == 'Y':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,0.15) -- (0.08,0) -- (0.16,0.15); \draw[{color}, line width=0.7pt] (0.08,0) -- (0.08,-0.15);}}"
    elif c == 'Z':
        return rf"\tikz[baseline=-0.6ex]{{\draw[{color}, line width=0.7pt] (0,0.15) -- (0.15,0.15) -- (0,-0.15) -- (0.15,-0.15);}}"
    else:
        return char

def transform_word_to_rytt(word):
    out = []
    for ch in word:
        if ch.isalpha():
            is_up = ch.isupper()
            out.append(get_glyph_tikz(ch, is_up))
        else:
            out.append(ch)
    return "".join(out)

print("TikZ RYTT Glyph Engine initialized.")
