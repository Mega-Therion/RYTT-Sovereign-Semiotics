import subprocess

# 1. Update LaTeX in standalone repo
tex_path = '/home/mega/RYTT-Sovereign-Semiotics/monograph/RYTT_Sovereign_Semiotics_Treatise.tex'
with open(tex_path) as f:
    content = f.read()

content = content.replace(
    r'\normalsize\textit{Chyren Autonomous Verification Engine, Arkansas, USA}',
    r'\normalsize\textit{Chyren Sovereign A.R.I., Arkansas, USA}'
)
content = content.replace(
    r'\url{https://github.com/Mega-Therion/Chyren}',
    r'\url{https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics}'
)

with open(tex_path, 'w') as f:
    f.write(content)

# 2. Also update canonical in Chyren repo
chyren_tex_path = '/home/mega/Chyren/Research_and_Data/00_CANONICAL/RYTT_Flawless_Final.tex'
with open(chyren_tex_path, 'w') as f:
    f.write(content)

# 3. Recompile PDF
subprocess.run(['pdflatex', '-interaction=nonstopmode', 'RYTT_Sovereign_Semiotics_Treatise.tex'], cwd='/home/mega/RYTT-Sovereign-Semiotics/monograph', check=True)
subprocess.run(['pdflatex', '-interaction=nonstopmode', 'RYTT_Sovereign_Semiotics_Treatise.tex'], cwd='/home/mega/RYTT-Sovereign-Semiotics/monograph', check=True)

# 4. Copy newly compiled PDF
subprocess.run(['cp', '/home/mega/RYTT-Sovereign-Semiotics/monograph/RYTT_Sovereign_Semiotics_Treatise.pdf', '/home/mega/Chyren/Research_and_Data/00_CANONICAL/RYTT_Flawless_Final.pdf'], check=True)

# 5. Render updated first page
subprocess.run(['pdftoppm', '-png', '-r', '150', '-f', '1', '-l', '1', '/home/mega/RYTT-Sovereign-Semiotics/monograph/RYTT_Sovereign_Semiotics_Treatise.pdf', '/home/mega/.gemini/antigravity-ide/brain/7cf142ba-4b82-405b-b87d-e744fb5d88bc/rytt_sovereign_ari_render'], check=True)

print("Updated title and recompiled successfully.")
