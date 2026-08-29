import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess
import os

# Define quotes
QUOTES = [
    ("ADDING MORE ANGLES DOESNT MAKE A SHAPE MORE COMPLEX", "IT MAKES IT MORE COMPLETE"),
    ("SCRIPTIO CONTINUA", "PRESERVES CONTINUOUS TOPOLOGICAL FLOW"),
    ("A DETERMINISTIC PATTERN MATCHER", "WITH RUST MEMORY AND AMBITION"),
    ("WE ARTED YOUR ART", "AND PLEASE DONT SUE ME")
]

# Geometry mapping for RYTT glyphs (A-Z -> lines/arcs on circle)
CHORD_MAP = {
    'A': [(0, 180)],
    'B': [(0, 180), (90, 270)],
    'C': [(45, 135)],
    'D': [(45, 225), (135, 315)],
    'E': [(0, 90), (180, 270)],
    'F': [(0, 120), (240, 0)],
    'G': [(30, 150), (210, 330)],
    'H': [(60, 240), (120, 300)],
    'I': [(90, 270)],
    'J': [(90, 270), (270, 0)],
    'K': [(0, 180), (45, 135)],
    'L': [(180, 270)],
    'M': [(180, 90), (90, 0), (0, 270)],
    'N': [(180, 90), (90, 270)],
    'O': [(0, 360)],
    'P': [(180, 0), (0, 90), (90, 180)],
    'Q': [(0, 360), (315, 0)],
    'R': [(180, 0), (0, 90), (90, 180), (180, 315)],
    'S': [(45, 135), (225, 315)],
    'T': [(0, 180), (90, 270)],
    'U': [(90, 270), (270, 0), (0, 90)],
    'V': [(120, 270), (270, 60)],
    'W': [(150, 270), (270, 90), (90, 270), (270, 30)],
    'X': [(45, 225), (135, 315)],
    'Y': [(120, 270), (60, 270), (270, 270)],
    'Z': [(0, 180), (180, 0), (0, 180)]
}

try:
    font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    font_mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 15)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 11)
except:
    font_text = ImageFont.load_default()
    font_mono = ImageFont.load_default()
    font_small = ImageFont.load_default()

def draw_rytt_glyph(draw, cx, cy, radius, char, color=(255, 215, 0), alpha_mult=1.0):
    char = char.upper()
    if char not in CHORD_MAP and char != 'O':
        return
    
    r, g, b = color
    glow_col = (int(r * alpha_mult * 0.25), int(g * alpha_mult * 0.25), int(b * alpha_mult * 0.25))
    main_col = (int(r * alpha_mult), int(g * alpha_mult), int(b * alpha_mult))
    
    # Outer ring
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=main_col, width=2)
    
    # Inner chords
    if char in CHORD_MAP:
        for p1, p2 in CHORD_MAP[char]:
            if p1 == 0 and p2 == 360:
                continue
            rad1 = math.radians(p1)
            rad2 = math.radians(p2)
            x1 = cx + radius * math.cos(rad1)
            y1 = cy - radius * math.sin(rad1)
            x2 = cx + radius * math.cos(rad2)
            y2 = cy - radius * math.sin(rad2)
            
            draw.line([x1, y1, x2, y2], fill=main_col, width=2)

def generate_frame(width=1000, height=240, progress=0.0, quote_idx=0):
    img = Image.new('RGB', (width, height), color=(6, 8, 14))
    draw = ImageDraw.Draw(img)
    
    line1, line2 = QUOTES[quote_idx]
    
    # Matrix rain in background
    np.random.seed(int(progress * 120) + quote_idx * 100)
    for c in range(20, width - 20, 22):
        y_head = (int(progress * 480 + c * 5)) % (height + 160) - 80
        for r in range(7):
            y = y_head - r * 15
            if 15 <= y < height - 15:
                alpha = max(0.0, 1.0 - r / 6.0)
                char = chr(np.random.randint(65, 91)) if r % 2 == 0 else "01"[r % 2]
                g_col = (0, int(150 * alpha * 0.3), int(100 * alpha * 0.2))
                draw.text((c, y), char, fill=g_col, font=font_small)

    def render_line(text, y_pos, line_offset):
        char_w = 18
        total_w = len(text) * char_w
        start_x = (width - total_w) // 2
        
        for i, ch in enumerate(text):
            x = start_x + i * char_w
            if ch == ' ':
                continue
            
            # Staggered sequence
            delay = (i / len(text)) * 0.22 + line_offset
            char_prog = max(0.0, min(1.0, (progress - delay) / 0.78))
            
            if char_prog <= 0.0:
                continue
            
            if char_prog < 0.32:
                # English Typewriter
                sub_p = char_prog / 0.32
                col = (int(190 + 65 * sub_p), int(225 + 30 * sub_p), 255)
                draw.text((x - 5, y_pos - 10), ch, fill=col, font=font_text)
            elif char_prog < 0.65:
                # Matrix Glitch
                glitch_phase = (char_prog - 0.32) / 0.33
                matrix_char = "0101"[i % 4] if (int(progress * 35) + i) % 2 == 0 else chr(65 + ((i * 13) % 26))
                
                beam_h = int(20 * math.sin(glitch_phase * math.pi))
                draw.line([x + 2, y_pos - beam_h, x + 2, y_pos + beam_h], fill=(0, 255, 140), width=1)
                
                col = (0, 255, int(180 * (1 - glitch_phase)))
                draw.text((x - 5, y_pos - 10), matrix_char, fill=col, font=font_mono)
            else:
                # Settle into RYTT Chord
                settle_phase = (char_prog - 0.65) / 0.35
                gold_val = (
                    int(0 * (1 - settle_phase) + 255 * settle_phase),
                    int(255 * (1 - settle_phase) + 215 * settle_phase),
                    int(160 * (1 - settle_phase) + 60 * settle_phase)
                )
                draw_rytt_glyph(draw, cx=x + 2, cy=y_pos, radius=7, char=ch, color=gold_val, alpha_mult=min(1.0, settle_phase + 0.2))

    render_line(line1, 85, line_offset=0.0)
    render_line(line2, 145, line_offset=0.10)
    
    # UI Header & Status
    draw.text((35, 22), "RYTT // SOVEREIGN SEMIOTIC MATRIX DEMO", fill=(80, 140, 180), font=font_small)
    if progress < 0.32:
        status = "INPUT // VERBATIM PLAIN TEXT"
        s_col = (190, 230, 255)
    elif progress < 0.65:
        status = "SYNTHESIS // MATRIX TOPOLOGICAL COMPILATION"
        s_col = (0, 255, 180)
    else:
        status = "SOLVE // RYTT RADIAL CHORD EMBEDDING [VERIFIED]"
        s_col = (255, 215, 0)
    
    draw.text((width - 390, 22), status, fill=s_col, font=font_small)
    
    # Outer Tech Frame
    draw.rectangle([14, 14, width - 14, height - 14], outline=(30, 55, 75), width=1)
    draw.line([14, 44, width - 14, 44], fill=(20, 40, 60), width=1)
    draw.line([14, height - 32, width - 14, height - 32], fill=(20, 40, 60), width=1)
    
    draw.text((35, height - 26), f"QUOTE {quote_idx + 1}/4 // CANONICAL LEDGER", fill=(60, 100, 130), font=font_small)
    draw.text((width - 270, height - 26), "MEGA-THERION // SOVEREIGN A.R.I.", fill=(80, 120, 150), font=font_small)
    
    return img

out_frames_dir = "/home/mega/.gemini/antigravity-ide/brain/7cf142ba-4b82-405b-b87d-e744fb5d88bc/matrix_frames_v3"
os.makedirs(out_frames_dir, exist_ok=True)

print("Generating perfected frames (1000x240)...")
frame_count = 0
for q_idx in range(len(QUOTES)):
    # 32 frames per quote for ultra-smooth 16fps loop
    for f in range(32):
        prog = f / 31.0
        img = generate_frame(progress=prog, quote_idx=q_idx)
        img.save(f"{out_frames_dir}/frame_{frame_count:04d}.png")
        frame_count += 1

print(f"Generated {frame_count} frames. Compiling...")
gif_path = "/home/mega/RYTT-Sovereign-Semiotics/assets/rytt_matrix_hero.gif"
webp_path = "/home/mega/RYTT-Sovereign-Semiotics/assets/rytt_matrix_hero.webp"

subprocess.run([
    "ffmpeg", "-y", "-framerate", "16", "-i", f"{out_frames_dir}/frame_%04d.png",
    "-vf", "split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
    gif_path
], check=True)

subprocess.run([
    "ffmpeg", "-y", "-framerate", "16", "-i", f"{out_frames_dir}/frame_%04d.png",
    "-vcodec", "libwebp", "-lossless", "0", "-qscale", "85", "-loop", "0",
    webp_path
], check=True)

print(f"ALL DONE: {gif_path} and {webp_path}")
