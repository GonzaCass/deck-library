"""User-selectable installations and paths; shell settings are read, never sourced."""
import configparser,json,os,pathlib,re,shutil,subprocess
from .models import Store,atomic_json

DEFAULTS={'rom_roots':[],'port_roots':[],'quiver_roots':[],'catalog_sources':[],'custom_ports':[],'prefer_ports':True,'emulators':{},'prism_roots':[],'wiicompiled_roots':[],'eden_config':'','view':'covers','catalog_url':'','onboarding_complete':False,'artwork_provider':'automatic','steamgriddb_key':'','animations':True,'check_updates':True,'auto_update':True,'auto_update_ports':False,'catalog_auto':True,'fix_controllers':True}

def settings(store=None):
    store=store or Store();path=store.root/'settings.json'
    value=json.loads(path.read_text()) if path.exists() else {}
    return {**DEFAULTS,**value}

def save_settings(value,store=None):
    store=store or Store();atomic_json(store.root/'settings.json',{**DEFAULTS,**value})

def emudeck_paths(home=None):
    home=pathlib.Path(home or pathlib.Path.home());file=home/'.config/EmuDeck/settings.sh';found={}
    if file.exists():
        for line in file.read_text().splitlines():
            match=re.fullmatch(r'\s*(emulationPath|romsPath|emusFolder|savesPath)\s*=\s*(.*?)\s*',line)
            if not match:continue
            raw=match.group(2).split(' #')[0].replace('"','').replace("'",'')
            raw=raw.replace('${HOME}',str(home)).replace('$HOME',str(home))
            if raw.startswith('/') and not any(c in raw for c in ('`','$','\n',';')):found[match.group(1)]=str(pathlib.Path(raw))
    root=pathlib.Path(found.get('emulationPath',home/'Emulation'))
    return {'installed':file.exists() or (home/'.config/EmuDeck/backend').is_dir(),'root':str(root),'roms':found.get('romsPath',str(root/'roms')),'launchers':str(root/'tools/launchers'),'apps':found.get('emusFolder',str(home/'Applications'))}

def flatpak_apps():
    try:return set(subprocess.check_output(['flatpak','list','--app','--columns=application'],text=True,stderr=subprocess.DEVNULL,timeout=10).splitlines())
    except (OSError,subprocess.TimeoutExpired,subprocess.CalledProcessError):return set()

def wiicompiled_roots(home=None,preferences=None):
    home=pathlib.Path(home or pathlib.Path.home());preferences=preferences or DEFAULTS
    candidates=[home/'.var/app/io.github.TeamWheelWizard.WheelWizard/data/WiiCompiled',home/'.local/share/WiiCompiled',*map(pathlib.Path,preferences.get('wiicompiled_roots',[]))]
    return list(dict.fromkeys(p for p in candidates if (p/'Config.toml').exists() or (p/'install-state.json').exists() or (p/'Install/Base/WiiCompiled').exists()))

def report(home=None,preferences=None):
    from .discovery import available_emulators,prism_installations
    home=pathlib.Path(home or pathlib.Path.home());preferences=preferences or DEFAULTS;emudeck=emudeck_paths(home)
    return {'emudeck':emudeck,'emulators':available_emulators(home,preferences),'prism':prism_installations(home,preferences),'wiicompiled':[str(p) for p in wiicompiled_roots(home,preferences)],'rom_roots':list(dict.fromkeys([emudeck['roms'],*preferences.get('rom_roots',[])])),'port_roots':list(dict.fromkeys([str(home/'ports'),*preferences.get('port_roots',[])]))}


def apps_folder(root):
    """Install folder of a Quiver/GithubLauncher root (settings.json may relocate it)."""
    root=pathlib.Path(root)
    try:
        value=json.loads((root/'settings.json').read_text(encoding='utf-8-sig')).get('AppsPath','')
        if value:return pathlib.Path(value).expanduser()
    except (OSError,ValueError):pass
    return root/'Apps'

def launcher_roots(home=None,preferences=None):
    """Quiver and GithubLauncher installs. Both keep apps.json, an Apps folder, version.txt and selected_executable.txt."""
    home=pathlib.Path(home or pathlib.Path.home());preferences=preferences or DEFAULTS
    roots=[home/'ports/quiver-launcher',home/'Applications/QuiverLauncher',home/'ports/GithubLauncher',home/'ports/github-launcher',home/'Applications/GithubLauncher',*map(pathlib.Path,preferences.get('quiver_roots',[]))]
    for parent in (home/'ports',home/'Applications'):
        try:children=[c for c in parent.iterdir() if c.is_dir()]
        except OSError:continue
        roots+=[c for c in children if (c/'apps.json').is_file() and (c/'settings.json').is_file()]
    return list(dict.fromkeys(r for r in roots if r.is_dir()))

def is_launcher_root(folder):
    folder=pathlib.Path(folder);return (folder/'apps.json').is_file() and (folder/'settings.json').is_file()
