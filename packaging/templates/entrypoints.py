import importlib.metadata
from pathlib import Path
import sys

try:
    from pip._vendor.distlib.scripts import ScriptMaker
except ImportError:
    from distlib.scripts import ScriptMaker

maker = ScriptMaker(None, str(Path(sys.executable).parent))
maker.executable = sys.executable
maker.clobber = True
maker.variants = {''}
for dist in importlib.metadata.distributions():
    for entry in dist.entry_points:
        if entry.group == 'console_scripts':
            maker.make(f'{entry.name} = {entry.value}')
