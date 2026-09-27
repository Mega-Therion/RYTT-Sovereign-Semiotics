#!/usr/bin/env python3
"""
RYTT Font Generator script.
Generates fonts/RYTT-Regular.ttf from RYTT_GENOME and RYTT_LIGATURES defined in font_compiler.py.
"""

import os
import sys
import importlib.util
import numpy as np
import svgpathtools
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
import fontTools.ttLib

def main():
    # Resolve directory paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    work_dir = os.path.dirname(script_dir) if os.path.basename(script_dir) == "scripts" else script_dir
    fonts_dir = os.path.join(work_dir, "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    ttf_path = os.path.join(fonts_dir, "RYTT-Regular.ttf")

    print(f"Work directory: {work_dir}")
    print(f"Target TTF path: {ttf_path}")

    # 1. Import RYTT_GENOME and RYTT_LIGATURES from the rytt package (src/)
    src_dir = os.path.join(work_dir, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from rytt.compiler import RYTT_GENOME as rytt_genome, RYTT_LIGATURES as rytt_ligatures

    print(f"Loaded {len(rytt_genome)} genome entries and {len(rytt_ligatures)} ligature entries.")

    # Convert SVG path data into TTF contours
    # Coordinate transform: units_per_em=1000, scale factor 10, y flipped: (10*x, 1000 - 10*y)
    def path_to_contours(path_str, key_name, samples_per_subpath=32):
        try:
            path = svgpathtools.parse_path(path_str)
            subpaths = path.continuous_subpaths()
            contours = []
            for sp in subpaths:
                pts = []
                for t in np.linspace(0, 1, samples_per_subpath):
                    p = sp.point(t)
                    xf = int(round(10 * p.real))
                    yf = int(round(1000 - 10 * p.imag))
                    pts.append((xf, yf))
                
                # Deduplicate consecutive points
                dedup_pts = []
                for pt in pts:
                    if not dedup_pts or pt != dedup_pts[-1]:
                        dedup_pts.append(pt)
                if len(dedup_pts) > 1 and dedup_pts[0] == dedup_pts[-1]:
                    dedup_pts.pop()
                
                # Ensure contour has > 2 points (at least 3)
                if len(dedup_pts) >= 3:
                    contours.append(dedup_pts)
                elif len(dedup_pts) > 0:
                    p0 = dedup_pts[0]
                    p1 = dedup_pts[-1] if len(dedup_pts) > 1 else (p0[0] + 10, p0[1] + 10)
                    mid = (int(round((p0[0] + p1[0]) / 2)), int(round((p0[1] + p1[1]) / 2)))
                    contours.append([p0, mid, p1])
            return contours
        except Exception as e:
            print(f"[WARNING] Failed to parse SVG path for key {key_name!r}: {e}")
            return None

    glyf_dict = {}
    hmetrics_dict = {}
    cmap_dict = {}
    glyph_order = [".notdef"]

    failed_keys = []

    # Setup .notdef glyph
    pen_notdef = TTGlyphPen(None)
    pen_notdef.moveTo((100, 0))
    pen_notdef.lineTo((900, 0))
    pen_notdef.lineTo((900, 1000))
    pen_notdef.lineTo((100, 1000))
    pen_notdef.closePath()
    pen_notdef.moveTo((200, 100))
    pen_notdef.lineTo((200, 900))
    pen_notdef.lineTo((800, 900))
    pen_notdef.lineTo((800, 100))
    pen_notdef.closePath()
    glyf_dict[".notdef"] = pen_notdef.glyph()
    hmetrics_dict[".notdef"] = (1000, 0)

    # 2. Process RYTT_GENOME (52 entries)
    for key, entry in rytt_genome.items():
        gname = f"glyph_{key}"
        glyph_order.append(gname)

        contours = path_to_contours(entry["path"], key)
        if contours is None:
            failed_keys.append(key)
            contours = []

        pen = TTGlyphPen(None)
        for c in contours:
            if not c:
                continue
            pen.moveTo(c[0])
            for pt in c[1:]:
                pen.lineTo(pt)
            pen.closePath()

        glyf_dict[gname] = pen.glyph()
        hmetrics_dict[gname] = (1000, 0)

        # PUA mapping
        pua_code = ord(entry["pua"])
        cmap_dict[pua_code] = gname

        # Plain ASCII mapping
        ascii_code = ord(key)
        cmap_dict[ascii_code] = gname

    # 3. Process RYTT_LIGATURES (46 entries)
    for key, entry in rytt_ligatures.items():
        gname = f"chord_{key}"
        glyph_order.append(gname)

        contours = path_to_contours(entry["path"], key)
        if contours is None:
            failed_keys.append(key)
            contours = []

        pen = TTGlyphPen(None)
        for c in contours:
            if not c:
                continue
            pen.moveTo(c[0])
            for pt in c[1:]:
                pen.lineTo(pt)
            pen.closePath()

        glyf_dict[gname] = pen.glyph()
        hmetrics_dict[gname] = (1000, 0)

        # PUA mapping (ligature source strings are multi-char -> only PUA codepoint mapped)
        pua_code = ord(entry["pua"])
        cmap_dict[pua_code] = gname

    # 4 & 6. FontBuilder Setup
    units_per_em = 1000
    fb = FontBuilder(units_per_em, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupGlyf(glyf_dict)
    fb.setupHorizontalMetrics(hmetrics_dict)
    fb.setupHorizontalHeader(ascent=1000, descent=0)
    fb.setupCharacterMap(cmap_dict)
    fb.setupNameTable({
        "familyName": "RYTT",
        "styleName": "Regular",
        "fullName": "RYTT Regular",
        "uniqueFontIdentifier": "RYTT-Sovereign-Semiotics; RYTT Regular; 2026",
        "psName": "RYTT-Regular"
    })
    fb.setupOS2(sTypoAscender=1000, sTypoDescender=0, usWinAscent=1000, usWinDescent=0)
    fb.setupPost()

    # 7. Write fonts/RYTT-Regular.ttf
    fb.save(ttf_path)
    print(f"\nFont successfully generated and saved to {ttf_path}")

    # 8. VALIDATION
    print("\n--- VALIDATION ---")
    tt = fontTools.ttLib.TTFont(ttf_path)

    # Check font opens
    assert tt is not None, "Failed to load TTF with fontTools"
    print("Assertion passed: TTF opens successfully.")

    # Check cmap entries
    loaded_cmap = tt.getBestCmap()
    pua_cmap = {k: v for k, v in loaded_cmap.items() if (0xE000 <= k <= 0xE8FF)}
    ascii_cmap = {k: v for k, v in loaded_cmap.items() if (0x41 <= k <= 0x5A) or (0x61 <= k <= 0x7A)}

    print(f"Total cmap entries: {len(loaded_cmap)}")
    print(f"  PUA mapped codepoints: {len(pua_cmap)} (expect 98 = 52 letters + 46 chords)")
    print(f"  ASCII mapped letters: {len(ascii_cmap)} (expect 52 = 26 lowercase + 26 uppercase)")

    assert len(pua_cmap) == 98, f"Expected 98 PUA codepoints, got {len(pua_cmap)}"
    assert len(ascii_cmap) == 52, f"Expected 52 ASCII codepoints, got {len(ascii_cmap)}"
    assert ".notdef" not in loaded_cmap.values(), ".notdef should not be mapped in cmap"
    print("Assertion passed: cmap codepoint counts match expectations (52 letters + 46 chords + 52 ASCII, 0 .notdef).")

    # Check glyph contours for all mapped codepoints
    glyf_table = tt["glyf"]
    summary_rows = []

    for cp, gname in sorted(loaded_cmap.items()):
        glyph = glyf_table[gname]
        num_contours = glyph.numberOfContours
        assert num_contours >= 1, f"Glyph {gname} (codepoint {hex(cp)}) has 0 contours"

        # Calculate points per contour
        end_pts = glyph.endPtsOfContours
        contour_pts = []
        prev = -1
        for ep in end_pts:
            pts_in_contour = ep - prev
            assert pts_in_contour > 2, f"Glyph {gname} contour has {pts_in_contour} points, expected >2"
            contour_pts.append(pts_in_contour)
            prev = ep

        tot_pts = sum(contour_pts)
        bounds = (glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax)
        summary_rows.append((hex(cp), gname, num_contours, tot_pts, bounds))

    print("Assertion passed: every mapped codepoint's glyph has at least 1 contour with >2 points.")

    # Summary table output
    print("\n--- SUMMARY TABLE (Mapped Codepoints) ---")
    print(f"{'Codepoint':<10} | {'Glyph Name':<15} | {'Contours':<8} | {'Total Pts':<10} | {'Bounds (xMin, yMin, xMax, yMax)'}")
    print("-" * 75)
    for row in summary_rows[:15]:  # Print first 15 entries
        print(f"{row[0]:<10} | {row[1]:<15} | {row[2]:<8} | {row[3]:<10} | {row[4]}")
    print(f"... and {len(summary_rows) - 15} more mapped entries.")

    # Tiny rendered-sample check: print bounding boxes for 5 sample glyphs
    print("\n--- RENDERED-SAMPLE CHECK (5 Sample Bounding Boxes) ---")
    sample_targets = ["glyph_A", "glyph_a", "chord_TION", "chord_tion", "glyph_Z"]
    for sample_gname in sample_targets:
        if sample_gname in glyf_table:
            g = glyf_table[sample_gname]
            print(f"Sample Glyph '{sample_gname}': bounds (xMin={g.xMin}, yMin={g.yMin}, xMax={g.xMax}, yMax={g.yMax}), contours={g.numberOfContours}")

    # Summary report
    print("\n--- FINAL STATUS ---")
    print("Status: TTF built successfully!")
    print(f"Mapped Codepoints: {len(pua_cmap)} PUA (52 letters + 46 chords) + {len(ascii_cmap)} ASCII")
    print(f"Failed Paths: {len(failed_keys)} {failed_keys if failed_keys else ''}")

if __name__ == "__main__":
    main()
