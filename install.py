#!/usr/bin/env python3
"""Install only Deck Library's own code/menu shortcut, never user games or Steam data."""
import argparse,pathlib,shlex,shutil,sys
if sys.version_info<(3,11):raise SystemExit('Deck Library requiere Python 3.11 o posterior (incluye tomllib).')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--destination',type=pathlib.Path,default=pathlib.Path.home()/'Applications/DeckLibrary')
p.add_argument('--desktop',action='store_true')
a=p.parse_args();source=pathlib.Path(__file__).resolve().parent;dest=a.destination.expanduser().resolve()
# Keep runtime data outside the installation so updates preserve the user's library.
dest.mkdir(parents=True,exist_ok=True)
for name in ('app.py','launch.sh','README.md','LEEME.md','LICENSE'):
 if source!=dest:shutil.copy2(source/name,dest/name)
for name in ('deck_library','assets','docs','presets'):
 if source!=dest:shutil.copytree(source/name,dest/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(dest/'launch.sh').chmod(0o755)
def quoted(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('`','\\`').replace('%','%%')+'"'
icon_dir=pathlib.Path.home()/'.local/share/icons/hicolor/scalable/apps';icon_dir.mkdir(parents=True,exist_ok=True);shutil.copy2(dest/'assets/icon.svg',icon_dir/'deck-library.svg')
entry='[Desktop Entry]\nType=Application\nName=Deck Library\nComment=Agregar ports y juegos emulados a Steam\nExec='+quoted(dest/'launch.sh')+'\nIcon=deck-library\nStartupWMClass=deck-library\nTerminal=false\nCategories=Game;Utility;\n'
menu=pathlib.Path.home()/'.local/share/applications/deck-library.desktop';menu.parent.mkdir(parents=True,exist_ok=True);menu.write_text(entry)
if a.desktop:
 desktop=pathlib.Path.home()/'Desktop';desktop.mkdir(exist_ok=True);target=desktop/'Deck Library.desktop';target.write_text(entry);target.chmod(0o755)
print('Instalado:',dest,'\nAbrí Deck Library desde el menú de aplicaciones.')
