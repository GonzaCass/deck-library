"""One tidy folder for what Deck Library creates: ~/DeckLibrary/{ports,roms,switch,iso}.

Existing installations keep working: a ~/ports folder that already has content stays the ports folder, and EmuDeck's ROM
folders are still scanned. The ROM folder here is for people who do not use EmuDeck."""
import pathlib

NAME='DeckLibrary'
SUBFOLDERS=('ports','roms','switch','iso')

def root(home=None):return pathlib.Path(home or pathlib.Path.home())/NAME

def folder(kind,home=None):
    if kind not in SUBFOLDERS:raise ValueError('Carpeta desconocida.')
    return root(home)/kind

def ensure(home=None):
    """Create the folder and its subfolders. Never raises: a read-only home just means nothing is created."""
    try:
        for kind in SUBFOLDERS:folder(kind,home).mkdir(parents=True,exist_ok=True)
    except OSError:return False
    return True

def legacy_ports_in_use(home=None):
    """True when ~/ports already holds installations from before this folder existed."""
    legacy=pathlib.Path(home or pathlib.Path.home())/'ports'
    try:return legacy.is_dir() and not legacy.is_symlink() and any(legacy.iterdir())
    except OSError:return False

def ports_folder(home=None):
    """Where ports are installed: the old ~/ports when it is in use, otherwise ~/DeckLibrary/ports."""
    return pathlib.Path(home or pathlib.Path.home())/'ports' if legacy_ports_in_use(home) else folder('ports',home)

def display_ports(home=None):
    """The ports folder as it is shown to people."""
    return '~/ports' if legacy_ports_in_use(home) else '~/'+NAME+'/ports'
