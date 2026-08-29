import shutil
import os
import subprocess

base_dir = '/home/mega/RYTT-Sovereign-Semiotics'
chyren_dir = '/home/mega/Chyren'

# 1. Copy Monograph LaTeX and PDF
shutil.copy('/home/mega/Chyren/Research_and_Data/00_CANONICAL/RYTT_Flawless_Final.tex', os.path.join(base_dir, 'monograph/RYTT_Sovereign_Semiotics_Treatise.tex'))
shutil.copy('/home/mega/Chyren/Research_and_Data/00_CANONICAL/RYTT_Flawless_Final.pdf', os.path.join(base_dir, 'monograph/RYTT_Sovereign_Semiotics_Treatise.pdf'))

# 2. Copy Python RYTT Core Implementation
if os.path.exists(os.path.join(chyren_dir, 'Codebase/l5_meaning/python/chyren/rytt')):
    for f in os.listdir(os.path.join(chyren_dir, 'Codebase/l5_meaning/python/chyren/rytt')):
        src_path = os.path.join(chyren_dir, 'Codebase/l5_meaning/python/chyren/rytt', f)
        if os.path.isfile(src_path):
            shutil.copy(src_path, os.path.join(base_dir, 'src/rytt', f))

# 3. Copy Interactive Web Renderers
shutil.copy(os.path.join(chyren_dir, 'apps/holonomic_rytt_stack.html'), os.path.join(base_dir, 'renderers/holonomic_rytt_stack.html'))
shutil.copy(os.path.join(chyren_dir, 'apps/blake_the_tyger_rytt.html'), os.path.join(base_dir, 'renderers/blake_the_tyger_rytt.html'))

# 4. Copy Tests & Benchmarks
if os.path.exists(os.path.join(chyren_dir, 'tests/test_rytt_native_lossless.py')):
    shutil.copy(os.path.join(chyren_dir, 'tests/test_rytt_native_lossless.py'), os.path.join(base_dir, 'tests/test_rytt_native_lossless.py') if os.path.exists(os.path.join(base_dir, 'tests')) else os.path.join(base_dir, 'benchmarks/test_rytt_native_lossless.py'))

print("Populated repository assets successfully.")
