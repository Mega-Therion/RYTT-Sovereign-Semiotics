from manim import *
import numpy as np


class RadialLexicon(Scene):
    def glyph(self, token, color, scale=1.0, stroke_width=3.0):
        t = token.lower()
        lw = stroke_width
        if t == "a":
            glyph = Dot(ORIGIN, radius=0.075, color=color)
        elif t == "b":
            glyph = VGroup(
                Line([0, -0.24, 0], [0, 0.24, 0]),
                Line([0, 0.03, 0], [0.21, 0.03, 0]),
                Line([0, 0.17, 0], [0.15, 0.17, 0]),
            )
        elif t == "c":
            glyph = VGroup(Line([0.18, 0.20, 0], [-0.18, 0, 0]), Line([-0.18, 0, 0], [0.18, -0.20, 0]))
        elif t == "d":
            glyph = VGroup(
                Line([0.18, 0.20, 0], [-0.18, 0, 0]),
                Line([-0.18, 0, 0], [0.18, -0.20, 0]),
                Dot(ORIGIN, radius=0.045, color=color),
            )
        elif t == "e":
            glyph = VGroup(RegularPolygon(n=4, radius=0.22).rotate(PI / 4), Dot(ORIGIN, radius=0.045, color=color))
        elif t == "f":
            glyph = RegularPolygon(n=4, radius=0.22).rotate(PI / 4)
        elif t == "g":
            glyph = Line([-0.24, 0, 0], [0.24, 0, 0])
        elif t == "h":
            glyph = VGroup(Line([-0.18, -0.22, 0], [-0.18, 0.22, 0]), Line([-0.18, 0.22, 0], [0.22, 0.22, 0]))
        elif t == "i":
            glyph = VGroup(
                Line([0.20, 0.20, 0], [-0.18, 0.20, 0]),
                Line([-0.18, 0.20, 0], [-0.18, -0.20, 0]),
                Line([-0.18, -0.20, 0], [0.20, -0.20, 0]),
                Dot(ORIGIN, radius=0.04, color=color),
            )
        elif t == "j":
            glyph = VGroup(Line([0.20, 0.20, 0], [-0.18, 0.20, 0]), Line([-0.18, 0.20, 0], [-0.18, -0.20, 0]), Line([-0.18, -0.20, 0], [0.20, -0.20, 0]))
        elif t == "k":
            glyph = Square(side_length=0.40)
        elif t == "l":
            glyph = Arc(radius=0.21, start_angle=PI / 2, angle=PI)
        elif t == "m":
            glyph = Arc(radius=0.23, start_angle=0, angle=PI)
        elif t == "n":
            glyph = VGroup(Arc(radius=0.17, start_angle=PI / 2, angle=PI).shift(LEFT * 0.10), Arc(radius=0.17, start_angle=-PI / 2, angle=PI).shift(RIGHT * 0.10))
        elif t == "o":
            glyph = VGroup(Arc(radius=0.17, start_angle=PI / 2, angle=PI).shift(LEFT * 0.10), Arc(radius=0.17, start_angle=-PI / 2, angle=PI).shift(RIGHT * 0.10), Dot(ORIGIN, radius=0.04, color=color))
        elif t == "p":
            glyph = VGroup(Arc(radius=0.22, start_angle=PI / 2, angle=PI).shift(LEFT * 0.10), Arc(radius=0.22, start_angle=-PI / 2, angle=PI).shift(RIGHT * 0.10))
        elif t == "q":
            glyph = Circle(radius=0.20)
        elif t == "r":
            glyph = VGroup(Circle(radius=0.20), Dot(ORIGIN, radius=0.04, color=color))
        elif t == "s":
            glyph = Line([0, -0.24, 0], [0, 0.24, 0])
        elif t == "t":
            glyph = VGroup(Line([-0.24, 0.21, 0], [0.24, 0.21, 0]), Line([0, 0.21, 0], [0, -0.24, 0]))
        elif t == "u":
            glyph = VGroup(Line([-0.10, -0.24, 0], [-0.10, 0.24, 0]), Dot([0.13, 0, 0], radius=0.04, color=color))
        elif t == "v":
            glyph = VGroup(Line([-0.20, 0.20, 0], [0, -0.22, 0]), Line([0, -0.22, 0], [0.20, 0.20, 0]))
        elif t == "w":
            glyph = VGroup(Line([-0.20, 0.20, 0], [0, -0.22, 0]), Line([0, -0.22, 0], [0.20, 0.20, 0]), Line([-0.12, 0, 0], [0.12, 0, 0]))
        elif t == "x":
            glyph = VGroup(Line([-0.20, 0.20, 0], [0.20, -0.20, 0]), Line([0.20, 0.20, 0], [-0.20, -0.20, 0]))
        elif t == "y":
            glyph = VGroup(Line([-0.20, 0.20, 0], [0, 0, 0]), Line([0, 0, 0], [0.20, 0.20, 0]), Line([0, 0, 0], [0, -0.24, 0]))
        elif t == "z":
            glyph = VGroup(Line([0, -0.24, 0], [0, 0.22, 0]), Line([-0.18, 0.05, 0], [0, 0.22, 0]), Line([0, 0.22, 0], [0.18, 0.05, 0]))
        else:
            glyph = Dot(ORIGIN, radius=0.05, color=color)
        glyph.set_stroke(color=color, width=lw, opacity=0.95)
        return glyph.scale(scale)

    def construct(self):
        ink = "#06080F"
        cyan = "#00E5FF"
        gold = "#C8A04E"
        bright_gold = "#E8C87C"
        parchment = "#F5ECD7"
        muted = "#7A6B50"

        background = Rectangle(width=config.frame_width, height=config.frame_height, stroke_width=0).set_fill(ink, opacity=1)
        frame = Rectangle(width=config.frame_width - 0.45, height=config.frame_height - 0.45, stroke_color=gold, stroke_width=1, stroke_opacity=0.34)
        frame2 = Rectangle(width=config.frame_width - 0.62, height=config.frame_height - 0.62, stroke_color=gold, stroke_width=0.5, stroke_opacity=0.16)
        self.add(background, frame, frame2)

        title = Text("RYTT SOVEREIGN SEMIOTICS", font="DejaVu Sans", font_size=28, color=bright_gold, weight=BOLD).to_edge(UP, buff=0.38)
        title.set_stroke(width=0)
        subtitle = Text("RADIAL YETT–TOPOLOGY TOKENIZATION", font="DejaVu Sans", font_size=17, color=parchment)
        subtitle.next_to(title, DOWN, buff=0.13)
        kicker = Text("A FORMAL LOSSLESS SEMIOTIC GRAMMAR", font="DejaVu Sans", font_size=11, color=muted)
        kicker.next_to(subtitle, DOWN, buff=0.12)

        radial_guides = VGroup(
            Circle(radius=2.62, color=gold, stroke_width=0.6, stroke_opacity=0.18),
            Circle(radius=2.38, color=gold, stroke_width=0.5, stroke_opacity=0.12),
            Circle(radius=1.68, color=gold, stroke_width=0.6, stroke_opacity=0.18),
            Circle(radius=1.12, color=cyan, stroke_width=0.6, stroke_opacity=0.18),
        ).shift(DOWN * 0.40)
        ticks = VGroup()
        for index in range(26):
            angle = PI / 2 - TAU * index / 26
            inner = np.array([2.49 * np.cos(angle), 2.49 * np.sin(angle) - 0.40, 0])
            outer = np.array([2.62 * np.cos(angle), 2.62 * np.sin(angle) - 0.40, 0])
            ticks.add(Line(inner, outer, color=gold, stroke_width=0.8, stroke_opacity=0.28))

        letters = list("abcdefghijklmnopqrstuvwxyz")
        chiral = set("fgjlpqr")
        cells = VGroup()
        for index, letter in enumerate(letters):
            angle = PI / 2 - TAU * index / 26
            point = np.array([2.38 * np.cos(angle), 2.38 * np.sin(angle) - 0.40, 0])
            color = gold if letter in chiral else cyan
            cell = RoundedRectangle(width=0.43, height=0.43, corner_radius=0.08, stroke_color=color, stroke_width=0.7, stroke_opacity=0.55)
            glyph = self.glyph(letter, color, scale=0.62, stroke_width=2.1)
            cells.add(VGroup(cell, glyph).move_to(point))

        seal_ring = Circle(radius=0.67, color=bright_gold, stroke_width=1.2, stroke_opacity=0.64).shift(DOWN * 0.40)
        seal_inner = Circle(radius=0.19, color=bright_gold, stroke_width=1.1, stroke_opacity=0.8).shift(DOWN * 0.40)
        seal_cross = VGroup(
            Line([-0.42, 0.28, 0], [0.42, 0.28, 0]),
            Line([0, 0.28, 0], [0, -0.34, 0]),
            Line([-0.30, -0.02, 0], [0.30, -0.02, 0]),
        ).shift(DOWN * 0.40).set_stroke(bright_gold, width=3.0, opacity=0.96)
        seal_text = Text("RYTT", font="DejaVu Sans", font_size=14, color=bright_gold, weight=BOLD).move_to(DOWN * 0.40)
        seal = VGroup(seal_ring, seal_inner, seal_cross, seal_text)

        ground_outline = RoundedRectangle(width=2.15, height=0.50, corner_radius=0.11, stroke_color=cyan, stroke_width=0.8, stroke_opacity=0.55)
        ground_text = Text("GROUND  ·  Z = 0", font="DejaVu Sans", font_size=13, color=cyan).move_to(ground_outline)
        ground_chip = VGroup(ground_outline, ground_text).move_to(LEFT * 4.70 + DOWN * 0.58)
        elevated_outline = RoundedRectangle(width=2.35, height=0.50, corner_radius=0.11, stroke_color=gold, stroke_width=0.8, stroke_opacity=0.55)
        elevated_text = Text("ELEVATED  ·  Z = 25", font="DejaVu Sans", font_size=13, color=gold).move_to(elevated_outline)
        elevated_chip = VGroup(elevated_outline, elevated_text).move_to(RIGHT * 4.62 + DOWN * 0.58)
        footer = Text("26 GEOMETRIC PRIMITIVES  ·  DUAL-PLANE ENCODING  ·  REVERSIBLE BY DESIGN", font="DejaVu Sans", font_size=10, color=muted).to_edge(DOWN, buff=0.38)

        self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(subtitle, shift=DOWN * 0.10), run_time=0.95)
        self.play(FadeIn(kicker), Create(radial_guides), Create(ticks), run_time=1.05)
        self.play(LaggedStart(*[FadeIn(cell, scale=0.72) for cell in cells], lag_ratio=0.045), run_time=2.25)
        self.play(Create(seal_ring), Create(seal_inner), Create(seal_cross), FadeIn(seal_text, scale=1.4), run_time=1.10)
        self.play(FadeIn(ground_chip, shift=RIGHT * 0.18), FadeIn(elevated_chip, shift=LEFT * 0.18), FadeIn(footer), run_time=0.65)
        self.play(Indicate(seal, color=bright_gold, scale_factor=1.08), run_time=0.60)
        self.wait(2.35)


class ChordCompiler(Scene):
    def glyph(self, token, color, scale=1.0, stroke_width=2.6):
        t = token.lower()
        if t == "t":
            glyph = VGroup(Line([-0.20, 0.18, 0], [0.20, 0.18, 0]), Line([0, 0.18, 0], [0, -0.20, 0]))
        elif t == "y":
            glyph = VGroup(Line([-0.18, 0.16, 0], [0, 0, 0]), Line([0, 0, 0], [0.18, 0.16, 0]), Line([0, 0, 0], [0, -0.20, 0]))
        elif t == "g":
            glyph = Line([-0.21, 0, 0], [0.21, 0, 0])
        elif t == "er":
            glyph = VGroup(RegularPolygon(n=4, radius=0.18).rotate(PI / 4), Circle(radius=0.075))
        elif t == "b":
            glyph = VGroup(Line([0, -0.20, 0], [0, 0.20, 0]), Line([0, 0.02, 0], [0.17, 0.02, 0]), Line([0, 0.14, 0], [0.12, 0.14, 0]))
        elif t == "u":
            glyph = VGroup(Line([-0.09, -0.20, 0], [-0.09, 0.20, 0]), Dot([0.12, 0, 0], radius=0.035, color=color))
        elif t == "r":
            glyph = VGroup(Circle(radius=0.17), Dot(ORIGIN, radius=0.035, color=color))
        elif t == "n":
            glyph = VGroup(Arc(radius=0.14, start_angle=PI / 2, angle=PI).shift(LEFT * 0.08), Arc(radius=0.14, start_angle=-PI / 2, angle=PI).shift(RIGHT * 0.08))
        elif t == "ing":
            glyph = VGroup(RegularPolygon(n=4, radius=0.18).rotate(PI / 4), Line([-0.18, 0, 0], [0.18, 0, 0]))
        elif t == "i":
            glyph = VGroup(Line([0.16, 0.16, 0], [-0.15, 0.16, 0]), Line([-0.15, 0.16, 0], [-0.15, -0.16, 0]), Line([-0.15, -0.16, 0], [0.16, -0.16, 0]), Dot(ORIGIN, radius=0.028, color=color))
        elif t == "h":
            glyph = VGroup(Line([-0.15, -0.17, 0], [-0.15, 0.17, 0]), Line([-0.15, 0.17, 0], [0.17, 0.17, 0]))
        elif t == "·":
            glyph = Dot(ORIGIN, radius=0.045, color="#7A6B50")
        elif t == ",":
            glyph = Text(",", font="DejaVu Sans", font_size=26, color="#7A6B50")
        else:
            glyph = Dot(ORIGIN, radius=0.045, color=color)
        glyph.set_stroke(color=color, width=stroke_width, opacity=0.96)
        return glyph.scale(scale)

    def token_cell(self, token, color):
        box = RoundedRectangle(width=0.48, height=0.54, corner_radius=0.09, stroke_color=color, stroke_width=0.8, stroke_opacity=0.58)
        glyph = self.glyph(token, color, scale=0.78, stroke_width=2.0).shift(UP * 0.045)
        label = Text(token.upper() if token in ("er", "ing") else token, font="DejaVu Sans", font_size=8, color=color).move_to(DOWN * 0.19)
        label.set_opacity(0.74)
        return VGroup(box, glyph, label)

    def construct(self):
        ink = "#06080F"
        cyan = "#00E5FF"
        gold = "#C8A04E"
        bright_gold = "#E8C87C"
        parchment = "#F5ECD7"
        muted = "#7A6B50"

        background = Rectangle(width=config.frame_width, height=config.frame_height, stroke_width=0).set_fill(ink, opacity=1)
        border = Rectangle(width=config.frame_width - 0.45, height=config.frame_height - 0.45, stroke_color=gold, stroke_width=0.8, stroke_opacity=0.26)
        self.add(background, border)

        title = Text("FROM LANGUAGE TO GEOMETRY", font="DejaVu Sans", font_size=29, color=bright_gold, weight=BOLD).to_edge(UP, buff=0.36)
        eyebrow = Text("GREEDY LONGEST-MATCH CHORD COMPILATION", font="DejaVu Sans", font_size=12, color=muted).next_to(title, DOWN, buff=0.12)
        source = Text("Tyger Tyger, burning bright,", font="DejaVu Sans", font_size=33, color=parchment).move_to(UP * 1.43)
        source_label = Text("SOURCE TEXT", font="DejaVu Sans", font_size=11, color=muted).next_to(source, LEFT, buff=0.22)

        underline = Line(source.get_left() + DOWN * 0.37, source.get_right() + DOWN * 0.37, color=gold, stroke_width=1.0, stroke_opacity=0.45)
        scanner = Line(DOWN * 0.35, UP * 0.35, color=bright_gold, stroke_width=2.2, stroke_opacity=0.9).move_to(source.get_left() + DOWN * 0.08)
        hint = Text("scan left to right", font="DejaVu Sans", font_size=10, color=bright_gold).next_to(scanner, DOWN, buff=0.10)

        first_er = SurroundingRectangle(source[3:5], color=gold, buff=0.045, corner_radius=0.05, stroke_width=1.4)
        second_er = SurroundingRectangle(source[9:11], color=gold, buff=0.045, corner_radius=0.05, stroke_width=1.4)
        ing = SurroundingRectangle(source[17:20], color=gold, buff=0.045, corner_radius=0.05, stroke_width=1.4)
        chord_labels = VGroup(
            Text("ER chord", font="DejaVu Sans", font_size=10, color=gold).next_to(first_er, UP, buff=0.08),
            Text("ER chord", font="DejaVu Sans", font_size=10, color=gold).next_to(second_er, UP, buff=0.08),
            Text("ING chord", font="DejaVu Sans", font_size=10, color=gold).next_to(ing, UP, buff=0.08),
        )

        tokens = ["T", "y", "g", "er", "·", "T", "y", "g", "er", ",", "·", "b", "u", "r", "n", "ing", "·", "b", "r", "i", "g", "h", "t", ","]
        cells = VGroup()
        for token in tokens:
            token_color = gold if token == "T" else cyan
            if token in ("·", ","):
                token_color = muted
            cells.add(self.token_cell(token, token_color))
        row_one = VGroup(*cells[:12]).arrange(RIGHT, buff=0.065)
        row_two = VGroup(*cells[12:]).arrange(RIGHT, buff=0.065)
        token_grid = VGroup(row_one, row_two).arrange(DOWN, buff=0.12).move_to(DOWN * 0.67)
        token_label = Text("RYTT TOKEN STREAM", font="DejaVu Sans", font_size=11, color=cyan).next_to(token_grid, UP, buff=0.17)

        metric_left = Text("28 source characters", font="DejaVu Sans", font_size=15, color=parchment)
        metric_arrow = Text("→", font="DejaVu Sans", font_size=20, color=gold)
        metric_right = Text("24 RYTT tokens", font="DejaVu Sans", font_size=15, color=cyan)
        metrics = VGroup(metric_left, metric_arrow, metric_right).arrange(RIGHT, buff=0.18).next_to(token_grid, DOWN, buff=0.33)
        recovery = Text("exact source recovery", font="DejaVu Sans", font_size=11, color=bright_gold).next_to(metrics, DOWN, buff=0.11)
        footer = Text("chords are chosen before single-letter primitives", font="DejaVu Sans", font_size=10, color=muted).to_edge(DOWN, buff=0.35)

        self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(eyebrow), run_time=0.72)
        self.play(FadeIn(source_label), Write(source), Create(underline), run_time=1.05)
        self.play(FadeIn(scanner), FadeIn(hint), run_time=0.35)
        self.play(scanner.animate.move_to(source.get_right() + DOWN * 0.08), FadeOut(hint), run_time=1.35)
        self.play(Create(first_er), Create(second_er), Create(ing), FadeIn(chord_labels), run_time=0.85)
        self.wait(0.45)
        self.play(FadeIn(token_label, shift=UP * 0.10), LaggedStart(*[FadeIn(cell, shift=UP * 0.18, scale=0.85) for cell in cells], lag_ratio=0.045), run_time=2.20)
        self.play(FadeIn(metrics, shift=UP * 0.10), FadeIn(recovery), FadeIn(footer), run_time=0.70)
        self.play(Indicate(metric_right, color=cyan, scale_factor=1.05), run_time=0.55)
        self.wait(2.40)


class DualPlaneCoordinate(Scene):
    def t_glyph(self, color, scale=1.0):
        glyph = VGroup(Line([-0.38, 0.33, 0], [0.38, 0.33, 0]), Line([0, 0.33, 0], [0, -0.38, 0]))
        return glyph.set_stroke(color=color, width=4.0, opacity=0.97).scale(scale)

    def chip(self, headline, detail, color, width=2.32):
        outline = RoundedRectangle(width=width, height=0.66, corner_radius=0.12, stroke_color=color, stroke_width=1.0, stroke_opacity=0.70)
        top = Text(headline, font="DejaVu Sans", font_size=13, color=color, weight=BOLD)
        bottom = Text(detail, font="DejaVu Sans", font_size=9, color="#7A6B50")
        words = VGroup(top, bottom).arrange(DOWN, buff=0.05)
        return VGroup(outline, words)

    def construct(self):
        ink = "#06080F"
        cyan = "#00E5FF"
        gold = "#C8A04E"
        bright_gold = "#E8C87C"
        parchment = "#F5ECD7"
        muted = "#7A6B50"

        background = Rectangle(width=config.frame_width, height=config.frame_height, stroke_width=0).set_fill(ink, opacity=1)
        border = Rectangle(width=config.frame_width - 0.45, height=config.frame_height - 0.45, stroke_color=gold, stroke_width=0.8, stroke_opacity=0.26)
        self.add(background, border)

        title = Text("CASE BECOMES A COORDINATE", font="DejaVu Sans", font_size=29, color=bright_gold, weight=BOLD).to_edge(UP, buff=0.36)
        subtitle = Text("THE SAME GEOMETRY OCCUPIES TWO DISJOINT PLANES", font="DejaVu Sans", font_size=12, color=muted).next_to(title, DOWN, buff=0.12)

        ground_plane = Polygon([-4.55, -1.55, 0], [0.15, -1.55, 0], [2.18, -0.62, 0], [-2.50, -0.62, 0], color=cyan, stroke_width=1.2, stroke_opacity=0.72)
        ground_plane.set_fill(cyan, opacity=0.075)
        elevated_plane = Polygon([-4.55, 0.62, 0], [0.15, 0.62, 0], [2.18, 1.55, 0], [-2.50, 1.55, 0], color=gold, stroke_width=1.2, stroke_opacity=0.72)
        elevated_plane.set_fill(gold, opacity=0.075)
        ground_grid = VGroup(*[Line([-4.15 + i * 0.75, -1.47, 0], [-2.10 + i * 0.75, -0.70, 0], color=cyan, stroke_width=0.45, stroke_opacity=0.23) for i in range(6)])
        elevated_grid = VGroup(*[Line([-4.15 + i * 0.75, 0.70, 0], [-2.10 + i * 0.75, 1.47, 0], color=gold, stroke_width=0.45, stroke_opacity=0.23) for i in range(6)])
        ground_label = Text("GROUND PLANE  ·  Z = 0", font="DejaVu Sans", font_size=14, color=cyan, weight=BOLD).move_to(LEFT * 3.25 + DOWN * 1.96)
        elevated_label = Text("ELEVATED PLANE  ·  Z = 25", font="DejaVu Sans", font_size=14, color=gold, weight=BOLD).move_to(LEFT * 2.92 + UP * 1.96)

        lower_t = self.t_glyph(cyan, scale=0.90).move_to(LEFT * 1.32 + DOWN * 1.12)
        upper_t = self.t_glyph(bright_gold, scale=0.90).move_to(LEFT * 1.32 + UP * 1.05)
        lower_label = Text("lowercase  t", font="DejaVu Sans", font_size=12, color=cyan).next_to(lower_t, RIGHT, buff=0.20)
        upper_label = Text("UPPERCASE  T", font="DejaVu Sans", font_size=12, color=gold).next_to(upper_t, RIGHT, buff=0.20)
        lift_line = DashedLine(lower_t.get_center() + UP * 0.38, upper_t.get_center() + DOWN * 0.38, color=parchment, dash_length=0.10, stroke_width=1.0, stroke_opacity=0.60)
        lift_arrow = Arrow(lower_t.get_center() + UP * 0.38, upper_t.get_center() + DOWN * 0.38, buff=0.08, color=bright_gold, stroke_width=2.0, max_tip_length_to_length_ratio=0.12)
        axis_label = Text("case axis", font="DejaVu Sans", font_size=10, color=parchment).next_to(lift_line, LEFT, buff=0.13)

        ground_chip = self.chip("GROUND TOKEN", "lowercase · PUA E000–E019", cyan, width=2.70).move_to(RIGHT * 4.62 + DOWN * 1.04)
        elevated_chip = self.chip("ELEVATED TOKEN", "UPPERCASE · PUA E800–E819", gold, width=2.86).move_to(RIGHT * 4.62 + UP * 1.07)
        distinction = Text("disjoint Unicode ranges preserve casing", font="DejaVu Sans", font_size=13, color=parchment).move_to(RIGHT * 3.70 + DOWN * 0.08)
        footer = Text("ONE GLYPH FAMILY  ·  TWO SPATIAL STATES  ·  NO EXTRA CASE METADATA", font="DejaVu Sans", font_size=10, color=muted).to_edge(DOWN, buff=0.34)

        self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(subtitle), run_time=0.72)
        self.play(Create(ground_plane), Create(elevated_plane), Create(ground_grid), Create(elevated_grid), FadeIn(ground_label), FadeIn(elevated_label), run_time=1.15)
        self.play(Create(lower_t), FadeIn(lower_label), run_time=0.62)
        self.play(Create(lift_line), GrowArrow(lift_arrow), TransformFromCopy(lower_t, upper_t), FadeIn(upper_label), FadeIn(axis_label), run_time=1.30)
        self.play(FadeIn(ground_chip, shift=LEFT * 0.15), FadeIn(elevated_chip, shift=LEFT * 0.15), run_time=0.65)
        self.play(FadeIn(distinction), FadeIn(footer), run_time=0.50)
        self.play(Indicate(upper_t, color=bright_gold, scale_factor=1.12), run_time=0.45)
        self.wait(2.10)


class LosslessReturn(Scene):
    def glyph(self, token, color, scale=1.0):
        t = token.lower()
        if t == "t":
            glyph = VGroup(Line([-0.16, 0.15, 0], [0.16, 0.15, 0]), Line([0, 0.15, 0], [0, -0.17, 0]))
        elif t == "y":
            glyph = VGroup(Line([-0.15, 0.14, 0], [0, 0, 0]), Line([0, 0, 0], [0.15, 0.14, 0]), Line([0, 0, 0], [0, -0.18, 0]))
        elif t == "g":
            glyph = Line([-0.18, 0, 0], [0.18, 0, 0])
        elif t == "er":
            glyph = VGroup(RegularPolygon(n=4, radius=0.15).rotate(PI / 4), Circle(radius=0.06))
        elif t == "ing":
            glyph = VGroup(RegularPolygon(n=4, radius=0.15).rotate(PI / 4), Line([-0.15, 0, 0], [0.15, 0, 0]))
        elif t == "r":
            glyph = VGroup(Circle(radius=0.14), Dot(ORIGIN, radius=0.025, color=color))
        elif t == "b":
            glyph = VGroup(Line([0, -0.17, 0], [0, 0.17, 0]), Line([0, 0.02, 0], [0.14, 0.02, 0]))
        elif t == "u":
            glyph = VGroup(Line([-0.07, -0.17, 0], [-0.07, 0.17, 0]), Dot([0.09, 0, 0], radius=0.024, color=color))
        elif t == "n":
            glyph = VGroup(Arc(radius=0.11, start_angle=PI / 2, angle=PI).shift(LEFT * 0.06), Arc(radius=0.11, start_angle=-PI / 2, angle=PI).shift(RIGHT * 0.06))
        elif t == "i":
            glyph = VGroup(Line([0.12, 0.12, 0], [-0.11, 0.12, 0]), Line([-0.11, 0.12, 0], [-0.11, -0.12, 0]), Line([-0.11, -0.12, 0], [0.12, -0.12, 0]))
        elif t == "h":
            glyph = VGroup(Line([-0.11, -0.12, 0], [-0.11, 0.12, 0]), Line([-0.11, 0.12, 0], [0.12, 0.12, 0]))
        elif t in ("·", ","):
            glyph = Dot(ORIGIN, radius=0.03, color="#7A6B50")
        else:
            glyph = Dot(ORIGIN, radius=0.035, color=color)
        return glyph.set_stroke(color=color, width=2.1, opacity=0.95).scale(scale)

    def construct(self):
        ink = "#06080F"
        cyan = "#00E5FF"
        gold = "#C8A04E"
        bright_gold = "#E8C87C"
        parchment = "#F5ECD7"
        muted = "#7A6B50"

        background = Rectangle(width=config.frame_width, height=config.frame_height, stroke_width=0).set_fill(ink, opacity=1)
        border = Rectangle(width=config.frame_width - 0.45, height=config.frame_height - 0.45, stroke_color=gold, stroke_width=0.8, stroke_opacity=0.26)
        self.add(background, border)

        title = Text("THE LOSSLESS RETURN", font="DejaVu Sans", font_size=29, color=bright_gold, weight=BOLD).to_edge(UP, buff=0.36)
        subtitle = Text("ENCODE, THEN RECONSTRUCT THE SAME SOURCE EXACTLY", font="DejaVu Sans", font_size=12, color=muted).next_to(title, DOWN, buff=0.12)
        source = Text("Tyger Tyger, burning bright,", font="DejaVu Sans", font_size=28, color=parchment).move_to(UP * 1.73)
        source_label = Text("SOURCE S", font="DejaVu Sans", font_size=10, color=muted).next_to(source, UP, buff=0.10)

        outer_ring = Circle(radius=1.42, color=gold, stroke_width=0.8, stroke_opacity=0.28).move_to(DOWN * 0.20)
        return_arc = Arc(radius=1.42, start_angle=-0.22 * PI, angle=1.66 * PI, color=cyan, stroke_width=2.2, stroke_opacity=0.78).move_to(DOWN * 0.20)
        arc_tip = Triangle(fill_color=cyan, fill_opacity=0.95, stroke_width=0).scale(0.10).rotate(0.18 * PI).move_to(return_arc.get_end())
        equation = VGroup(
            Text("D(", font="DejaVu Sans", font_size=46, color=cyan),
            Text("C(", font="DejaVu Sans", font_size=46, color=gold),
            Text("S", font="DejaVu Sans", font_size=46, color=parchment),
            Text("))  ≡  S", font="DejaVu Sans", font_size=46, color=cyan),
        ).arrange(RIGHT, buff=0.02).move_to(DOWN * 0.20)
        encode_label = Text("C(S)  ·  encode", font="DejaVu Sans", font_size=10, color=gold).move_to(LEFT * 1.30 + DOWN * 1.12)
        decode_label = Text("D(·)  ·  decompile", font="DejaVu Sans", font_size=10, color=cyan).move_to(RIGHT * 1.30 + DOWN * 1.12)

        raw_tokens = ["T", "y", "g", "er", "·", "T", "y", "g", "er", "·", "b", "u", "r", "n", "ing", "·", "b", "r", "i", "g", "h", "t"]
        stream = VGroup()
        for index, token in enumerate(raw_tokens):
            angle = PI / 2 - TAU * index / len(raw_tokens)
            radius = 2.05
            point = np.array([radius * np.cos(angle), radius * np.sin(angle) - 0.20, 0])
            color = gold if token == "T" else cyan
            if token == "·":
                color = muted
            cell = RoundedRectangle(width=0.35, height=0.35, corner_radius=0.07, stroke_color=color, stroke_width=0.6, stroke_opacity=0.52)
            glyph = self.glyph(token, color, scale=0.72)
            stream.add(VGroup(cell, glyph).move_to(point))
        token_caption = Text("RYTT token stream", font="DejaVu Sans", font_size=10, color=cyan).move_to(DOWN * 2.53)

        recovery_box = RoundedRectangle(width=7.25, height=0.62, corner_radius=0.12, stroke_color=cyan, stroke_width=1.0, stroke_opacity=0.56).move_to(DOWN * 2.91)
        recovery_text = Text("Tyger Tyger, burning bright,", font="DejaVu Sans", font_size=21, color=parchment).move_to(recovery_box.get_center())
        recovery_label = Text("D(C(S)) reproduces the original source string", font="DejaVu Sans", font_size=10, color=bright_gold).next_to(recovery_box, DOWN, buff=0.09)
        footer = Text("EXACT ROUNDTRIP  ·  FORMAL LEAN 4 PROOFS IN THE REPOSITORY", font="DejaVu Sans", font_size=10, color=muted).to_edge(DOWN, buff=0.34)

        self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(subtitle), run_time=0.72)
        self.play(FadeIn(source_label), Write(source), run_time=0.76)
        self.play(Create(outer_ring), LaggedStart(*[FadeIn(token, scale=0.7) for token in stream], lag_ratio=0.035), FadeIn(token_caption), run_time=1.70)
        self.play(FadeIn(equation, scale=0.90), FadeIn(encode_label), run_time=0.60)
        self.play(Create(return_arc), FadeIn(arc_tip), FadeIn(decode_label), run_time=1.05)
        self.play(LaggedStart(*[FadeOut(token, scale=0.70) for token in stream], lag_ratio=0.018), FadeIn(recovery_box, scale=0.96), FadeIn(recovery_text), run_time=1.10)
        self.play(FadeIn(recovery_label), FadeIn(footer), Indicate(equation, color=bright_gold, scale_factor=1.05), run_time=0.70)
        self.wait(2.10)
