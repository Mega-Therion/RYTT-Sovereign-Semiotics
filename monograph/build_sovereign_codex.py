import subprocess
import os
import re
import sys

sys.path.insert(0, '/home/mega/RYTT-Sovereign-Semiotics/src')
from rytt.compiler import RyttCompiler

# Load the base clean monograph
with open('/home/mega/RYTT-Sovereign-Semiotics/monograph/RYTT_Sovereign_Semiotics_Treatise.tex') as f:
    src = f.read()

# Build the Sovereign Codex LaTeX Document
codex_preamble = r'''\documentclass[11pt,oneside,letterpaper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb,amsthm,mathtools,bm}
\usepackage{microtype}
\usepackage[margin=1.05in,top=1.15in,bottom=1.15in]{geometry}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{colortbl}
\usepackage{enumitem}
\usepackage{tikz}
\usepackage{tikz-cd}
\usetikzlibrary{shapes,arrows.meta,positioning,calc,3d,decorations.pathreplacing,matrix,backgrounds,fit}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{eso-pic}
\usepackage{mdframed}
\usepackage{lastpage}
\usepackage{setspace}

\setstretch{1.06}
\setlength{\parskip}{0.45em}
\setlength{\parindent}{0pt}
\widowpenalty=10000
\clubpenalty=10000
\raggedbottom

% --- Sovereign Alien Codex Palette ---
\definecolor{void}{HTML}{04070F}
\definecolor{deep}{HTML}{080D1A}
\definecolor{panel}{HTML}{0B1221}
\definecolor{surface}{HTML}{111A2E}
\definecolor{gold}{HTML}{D4A843}
\definecolor{cyan}{HTML}{3ECFDE}
\definecolor{violet}{HTML}{9B6EF3}
\definecolor{green}{HTML}{3DD68C}
\definecolor{red}{HTML}{E05E6D}
\definecolor{ink}{HTML}{DCE8FF}
\definecolor{inkdim}{HTML}{7A92B8}
\definecolor{inkfaint}{HTML}{3A4E6E}

\usepackage[colorlinks=true, linkcolor=cyan, citecolor=cyan, urlcolor=gold]{hyperref}
\pagecolor{void}
\color{ink}

% --- Code Block Styling ---
\lstset{
  backgroundcolor=\color{deep},
  basicstyle=\ttfamily\scriptsize\color{ink},
  breaklines=true,
  captionpos=b,
  commentstyle=\color{inkdim},
  keywordstyle=\color{cyan}\bfseries,
  stringstyle=\color{gold},
  frame=single,
  framerule=0.6pt,
  rulecolor=\color{gold!40},
  numbers=left,
  numbersep=6pt,
  numberstyle=\tiny\color{inkfaint},
  showspaces=false,
  showstringspaces=false,
  tabsize=2
}

% --- Ambient Blueprint Grid & HUD Corner Brackets ---
\newcommand{\CodexBG}{%
  \AtPageLowerLeft{%
    \begin{tikzpicture}
      \useasboundingbox (0,0) rectangle (\paperwidth,\paperheight);
      % Blueprint Grid (Fine & Major)
      \begin{scope}[opacity=0.035]
        \draw[cyan, step=5mm] (0,0) grid (\paperwidth,\paperheight);
      \end{scope}
      \begin{scope}[opacity=0.07]
        \draw[cyan, step=25mm, line width=0.5pt] (0,0) grid (\paperwidth,\paperheight);
      \end{scope}
      % Sovereign HUD Outer Frame & Corner Brackets
      \draw[gold, opacity=0.40, line width=0.6pt]
        ($(0,0)+(14mm,14mm)$) rectangle ($(\paperwidth,\paperheight)-(14mm,14mm)$);
      % Corner ticks
      \foreach \c in {(14mm,14mm), (\paperwidth-14mm,14mm), (14mm,\paperheight-14mm), (\paperwidth-14mm,\paperheight-14mm)}{
        \fill[gold, opacity=0.8] \c circle (1.2pt);
      }
    \end{tikzpicture}}}
\AddToShipoutPictureBG{\CodexBG}

% --- Headers & Footers ---
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{}
\fancyhead[C]{}
\fancyhead[R]{}
\fancyfoot[C]{\small\color{inkdim} Page \thepage\ of \pageref{LastPage} $\quad\cdot\quad$ \color{gold}\textsc{RYTT Sovereign Semiotic Codex}}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% --- Section Formats ---
\titleformat{\section}{\large\bfseries\scshape\color{gold}}{\thesection.}{0.6em}{}[{\vspace{0.15em}\color{gold!50}\hrule height 0.6pt}]
\titleformat{\subsection}{\normalsize\bfseries\color{cyan}}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}{\normalsize\bfseries\color{violet}}{\thesubsubsection}{0.4em}{}
\titlespacing*{\section}{0pt}{1.8ex plus 0.2ex minus 0.1ex}{0.8ex}
\titlespacing*{\subsection}{0pt}{1.4ex plus 0.15ex minus 0.1ex}{0.5ex}

% --- Theorem & Panel Environments ---
\mdfdefinestyle{codexpanel}{
  linecolor=gold, linewidth=0.8pt, backgroundcolor=panel, fontcolor=ink,
  leftline=true, topline=false, bottomline=false, rightline=false,
  innerleftmargin=12pt, innerrightmargin=12pt, innertopmargin=8pt, innerbottommargin=8pt,
  skipabove=8pt, skipbelow=8pt, roundcorner=2pt
}
\theoremstyle{definition}
\newmdtheoremenv[style=codexpanel]{theorem}{\color{gold}Theorem}[section]
\newmdtheoremenv[style=codexpanel]{definition}{\color{gold}Definition}[section]
\newmdtheoremenv[style=codexpanel]{proposition}{\color{cyan}Proposition}[section]
\newmdtheoremenv[style=codexpanel]{lemma}{\color{cyan}Lemma}[section]

\setlist[itemize]{noitemsep, topsep=3pt, leftmargin=1.6em}
\setlist[enumerate]{noitemsep, topsep=3pt, leftmargin=1.6em}
'''

# Title & Author Block
codex_title = r'''\title{\vspace{-0.5cm}{\huge\bfseries\scshape\color{gold} RYTT Sovereign Semiotics:}\\[0.3em]
{\Large\bfseries\color{ink} A Formal Polytopic Semiotic Grammar, Dual-Plane Coordinate Algebra, Native Integer Chord Tokenization, and Lossless Holonomic Invariants}\\[0.45em]
{\large\normalfont\scshape\color{cyan} Sovereign Alien Codex Edition $\cdot$ Compiled Native Semiotic Monograph}}

\author{\textbf{\color{gold}R. W. Yett}\\[0.20em]
\normalsize\color{inkdim} Arkansas, USA $\cdot$ \texttt{\color{cyan}ORCID: 0009-0001-1303-7190}\\[0.12em]
\normalsize\color{inkdim} Correspondence: \texttt{\color{gold}R11110001Y@proton.me}\\[0.35em]
\normalsize\textit{\color{cyan}Chyren Sovereign A.R.I., Arkansas, USA}\\[0.20em]
\normalsize\url{https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics}}
\date{\today}'''

# Extract main body
body_start = src.find(r'\begin{abstract}')
body_text = src[body_start:]

# Replace standard colors with sovereign codex colors
body_text = body_text.replace('sovCobalt', 'cyan')
body_text = body_text.replace('sovAmber', 'gold')
body_text = body_text.replace('sovSlate', 'inkdim')
body_text = body_text.replace('sovTeal', 'green')
body_text = body_text.replace('cardbg', 'surface')
body_text = body_text.replace('cardborder', 'gold!40')
body_text = body_text.replace('codebg', 'deep')
body_text = body_text.replace('codegray', 'inkdim')

# Create the full Sovereign Codex Document
full_codex_tex = codex_preamble + '\n\n' + codex_title + '\n\n\\begin{document}\n\n\\maketitle\n\n' + body_text

with open('/home/mega/RYTT-Sovereign-Semiotics/monograph/RYTT_Sovereign_Codex_Treatise.tex', 'w') as f:
    f.write(full_codex_tex)

print("Generated RYTT_Sovereign_Codex_Treatise.tex successfully.")

# Compile PDF twice
subprocess.run(['pdflatex', '-interaction=nonstopmode', 'RYTT_Sovereign_Codex_Treatise.tex'], cwd='/home/mega/RYTT-Sovereign-Semiotics/monograph', check=True)
subprocess.run(['pdflatex', '-interaction=nonstopmode', 'RYTT_Sovereign_Codex_Treatise.tex'], cwd='/home/mega/RYTT-Sovereign-Semiotics/monograph', check=True)

# Render pages to PNG
subprocess.run(['pdftoppm', '-png', '-r', '150', '/home/mega/RYTT-Sovereign-Semiotics/monograph/RYTT_Sovereign_Codex_Treatise.pdf', '/home/mega/.gemini/antigravity-ide/brain/7cf142ba-4b82-405b-b87d-e744fb5d88bc/rytt_codex_edition_render'], check=True)

print("Compiled and rendered Sovereign Codex Monograph successfully.")
