#!/usr/bin/env python3
"""Install only Deck Library's own code/menu shortcut, never user games or Steam data."""
import argparse,pathlib,shlex,shutil,subprocess,sys
if sys.version_info<(3,11):raise SystemExit('Deck Library requiere Python 3.11 o posterior (incluye tomllib).')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--destination',type=pathlib.Path,default=pathlib.Path.home()/'Applications/DeckLibrary')
p.add_argument('--desktop',action='store_true')
a=p.parse_args();source=pathlib.Path(__file__).resolve().parent;dest=a.destination.expanduser().resolve()
# Keep runtime data outside the installation so updates preserve the user's library.
dest.mkdir(parents=True,exist_ok=True)
# Release archives carry a zero modification time. Python trusts a compiled cache whose source time and size match, so files are
# copied with the current time and old caches are removed; otherwise a same-length edit (a version number) would keep running the old code.
for name in ('app.py','launch.sh','README.md','LEEME.md','LICENSE'):
 if source!=dest:shutil.copy(source/name,dest/name)
for name in ('deck_library','assets','docs','presets','catalog','community'):
 if name in ('community','catalog') and not (source/name).is_dir():continue
 if source!=dest:shutil.copytree(source/name,dest/name,dirs_exist_ok=True,copy_function=shutil.copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.env','*.sqlite3*'))
for cache in dest.rglob('__pycache__'):shutil.rmtree(cache,ignore_errors=True)
(dest/'launch.sh').chmod(0o755)
def quoted(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('`','\\`').replace('%','%%')+'"'
icon_dir=pathlib.Path.home()/'.local/share/icons/hicolor/scalable/apps';icon_dir.mkdir(parents=True,exist_ok=True)
# Replace the file (new inode, fresh time) so the desktop's icon cache notices it, then ask the usual tools to refresh.
target=icon_dir/'deck-library.svg';temporary=target.with_name('.deck-library.svg.new');shutil.copy(dest/'assets/icon.svg',temporary);temporary.replace(target)
for tool in (['gtk-update-icon-cache','-f','-t',str(pathlib.Path.home()/'.local/share/icons/hicolor')],['kbuildsycoca6','--noincremental']):
 if shutil.which(tool[0]):subprocess.run(tool,capture_output=True,timeout=60)
entry='[Desktop Entry]\nType=Application\nName=Deck Library\nComment=Agregar ports y juegos emulados a Steam\nExec='+quoted(dest/'launch.sh')+'\nIcon=deck-library\nStartupWMClass=deck-library\nTerminal=false\nCategories=Game;Utility;\n'
menu=pathlib.Path.home()/'.local/share/applications/deck-library.desktop';menu.parent.mkdir(parents=True,exist_ok=True);menu.write_text(entry)
if a.desktop or (pathlib.Path.home()/'Desktop/Deck Library.desktop').is_file():
 desktop=pathlib.Path.home()/'Desktop';desktop.mkdir(exist_ok=True);target=desktop/'Deck Library.desktop';target.write_text(entry);target.chmod(0o755)
# Refresh our existing template so upgrades keep native stick input.
# This file belongs to Deck Library; Steam configsets and custom layouts stay untouched.
sys.path.insert(0,str(dest))
try:
 from deck_library import controllers
 from deck_library.steam import find_accounts
 for account in find_accounts():
  if (controllers.templates_dir(account)/controllers.LIBRARY_TEMPLATE).is_file():controllers.library_template(account)
except (OSError,ValueError,ImportError) as error:print('Perfil de mando:',error)
try:
 from deck_library.library_app import refresh_existing_art,refresh_existing_launcher
 if refresh_existing_launcher(app=dest/'app.py'):print('Acceso de Steam actualizado a la instalación actual.')
 count=refresh_existing_art(app=dest/'app.py')
 if count:print('Arte de Deck Library preparado para Steam:',count)
except (OSError,ValueError,ImportError) as error:print('Arte de Steam:',error)
print('Instalado:',dest,'\nDeck Library está disponible en el menú de aplicaciones.')
