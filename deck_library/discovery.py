"""Read-only discovery. Never downloads, moves or opens games."""
import json,os,pathlib,re,shutil,configparser,subprocess
from .models import Entry,Store
from .installations import emudeck_paths,settings,wiicompiled_roots
from .content import switch_id

# Extensions are restricted to bootable files; updates/DLC are excluded separately.
SYSTEMS={
 'switch':('Switch','eden',('-f','-g'),{'.nsp','.xci'}),
 'wii':('Wii','dolphin-emu',('-b','-e'),{'.iso','.rvz','.wbfs','.gcz'}),
 'gc':('GameCube','dolphin-emu',('-b','-e'),{'.iso','.rvz','.gcz'}),
 'psx':('PlayStation','duckstation',('-batch','-fullscreen'),{'.cue','.chd','.pbp','.m3u'}),
 'ps2':('PlayStation 2','pcsx2-qt',('-batch','-fullscreen'),{'.iso','.chd','.m3u'}),
 'psp':('PSP','ppsspp',('--fullscreen',),{'.iso','.cso','.pbp'}),
 '3ds':('Nintendo 3DS','azahar',('-f',),{'.3ds','.cci','.cxi'}),
 'n3ds':('Nintendo 3DS','azahar',('-f',),{'.3ds','.cci','.cxi'}),
 'gba':('Game Boy Advance','mgba',('-f',),{'.gba'}),
 'gb':('Game Boy','mgba',('-f',),{'.gb'}),
 'gbc':('Game Boy Color','mgba',('-f',),{'.gbc'}),
 'wiiu':('Wii U','cemu',('-f','-g'),{'.wua','.wud','.wux','.rpx'}),
}
EMULATOR_FLATPAKS={'mgba':'io.mgba.mGBA','eden':'dev.eden_emu.eden','dolphin-emu':'org.DolphinEmu.dolphin-emu','duckstation':'org.duckstation.DuckStation','pcsx2-qt':'net.pcsx2.PCSX2','ppsspp':'org.ppsspp.PPSSPP','azahar':'org.azahar_emu.Azahar','cemu':'info.cemu.Cemu'}
REJECT_PARTS={'updates','update','dlc','mods','duplicates','firmware','keys','sistemas','systems','bios'}

def nice_name(path):
    return re.sub(r'\s*\[[^]]*\]','',path.stem).replace('_',' ').strip()

def is_base_rom(path):
    if any(p.lower() in REJECT_PARTS for p in path.parts):return False
    match=re.search(r'\[(010[0-9a-fA-F]{13})\]',path.name)
    if match and int(match.group(1),16)&0x1fff:return False
    return True

def available_emulators(home=None,preferences=None):
    home=pathlib.Path(home or pathlib.Path.home());preferences=preferences or {};result={};emudeck=emudeck_paths(home)
    flatpaks=EMULATOR_FLATPAKS
    for label,slug,flags,_ in SYSTEMS.values():
        if slug in result:continue
        configured=preferences.get('emulators',{}).get(slug)
        launcher=pathlib.Path(emudeck['launchers'])/(slug+'.sh')
        apps=pathlib.Path(emudeck['apps']);images=sorted(p for p in apps.glob('*.AppImage') if p.name.lower().startswith(slug.split('-')[0]))
        binary=shutil.which(slug)
        app_id=flatpaks.get(slug,'')
        if configured:command=configured if isinstance(configured,list) else [configured]
        elif slug=='eden' and images:command=[str(images[0])]
        elif launcher.is_file():command=[str(launcher)]
        elif images:command=[str(images[0])]
        elif binary:command=[binary]
        elif (home/'.var/app'/app_id).is_dir():command=['/usr/bin/flatpak','run',app_id]
        else:continue
        result[slug]={'name':('Eden' if slug=='eden' else label),'command':command,'flags':list(flags)}
    return result


def prism_installations(home=None,preferences=None):
    home=pathlib.Path(home or pathlib.Path.home());preferences=preferences or {};result=[]
    roots=[home/'.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher',home/'.local/share/PrismLauncher',*map(pathlib.Path,preferences.get('prism_roots',[]))]
    binary=shutil.which('prismlauncher');images=sorted((home/'Applications').glob('*[Pp]rism*.AppImage'))
    for root in dict.fromkeys(roots):
        if not root.is_dir():continue
        if '.var/app/org.prismlauncher.PrismLauncher/' in str(root):command=['/usr/bin/flatpak','run','org.prismlauncher.PrismLauncher']
        elif binary:command=[binary]
        elif images:command=[str(images[0])]
        else:continue
        parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str
        file=root/'prismlauncher.cfg'
        if file.exists():
            text=file.read_text(errors='replace');parser.read_string(text if text.lstrip().startswith('[') else '[General]\n'+text)
        section=parser['General'] if parser.has_section('General') else {}
        instances=pathlib.Path(section.get('InstanceDir','instances'));icons=pathlib.Path(section.get('IconsDir','icons'))
        if not instances.is_absolute():instances=root/instances
        if not icons.is_absolute():icons=root/icons
        result.append({'root':str(root),'instances':str(instances),'icons':str(icons),'command':command})
    return result


def prism_entries(home=None,preferences=None):
    found=[]
    try:
        versions=dict(line.split('\t',1) for line in subprocess.check_output(['flatpak','list','--app','--columns=application,version'],text=True,stderr=subprocess.DEVNULL,timeout=5).splitlines() if '\t' in line)
    except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired):versions={}
    for install in prism_installations(home,preferences):
        for cfg in sorted(pathlib.Path(install['instances']).glob('*/instance.cfg')):
            parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str
            try:
                text=cfg.read_text(errors='replace');parser.read_string(text if text.lstrip().startswith('[') else '[General]\n'+text)
                section=parser['General'];name=section.get('name',cfg.parent.name);icon_key=section.get('iconKey','');cover=''
                if pathlib.Path(icon_key).name==icon_key:
                    for ext in ('.png','.jpg','.svg'):
                        icon=pathlib.Path(install['icons'])/(icon_key+ext)
                        if icon.exists():cover=str(icon);break
                version=''
                pack=cfg.parent/'mmc-pack.json'
                if pack.exists():version=next((c.get('version','') for c in json.loads(pack.read_text()).get('components',[]) if c.get('uid')=='net.minecraft'),'')
                command=install['command']+['--dir',install['root'],'--launch',cfg.parent.name]
                found.append(Entry(name,command,'minecraft','Minecraft',str(cfg),install['root'],cover=cover,game_id='minecraft-java',metadata={'adapter':'prism','instance_id':cfg.parent.name,'instance_root':str(cfg.parent),'version':version,'recommended_layout':'minecraft-keyboard-mouse','emulator_version':versions.get('org.prismlauncher.PrismLauncher','')}))
            except (OSError,ValueError,configparser.Error):continue
    return found

def scan(home=None,extra_roots=(),preferences=None):
    home=pathlib.Path(home or pathlib.Path.home());preferences=preferences if preferences is not None else settings(Store(home/'.local/share/deck-library'))
    found={};emulators=available_emulators(home,preferences)
    roots=list(dict.fromkeys([pathlib.Path(emudeck_paths(home)['roms']),*map(pathlib.Path,preferences.get('rom_roots',[])),*map(pathlib.Path,extra_roots)]))
    for root in roots:
        if not root.is_dir():continue
        for system,(label,slug,flags,exts) in SYSTEMS.items():
            folder=root/system
            if not folder.is_dir() or slug not in emulators:continue
            for path in folder.rglob('*'):
                if not path.is_file() or path.suffix.lower() not in exts or not is_base_rom(path):continue
                e=Entry(nice_name(path),emulators[slug]['command']+list(flags)+[str(path)],'emulated',label,str(path),mods=True)
                found[e.id]=e
    # Additional Switch folders already configured by the user (for example a microSD).
    qt=pathlib.Path(preferences.get('eden_config') or home/'.config/eden')/'qt-config.ini'
    if qt.is_file() and 'eden' in emulators:
        parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str;parser.read(qt)
        for section in parser.values():
            for key,value in section.items():
                if 'gamedirs' not in key or not key.endswith('\\path'):continue
                folder=pathlib.Path(value.strip('"'))
                if not folder.is_dir():continue
                for path in folder.rglob('*'):
                    if not path.is_file() or path.suffix.lower() not in ('.nsp','.xci') or not is_base_rom(path):continue
                    e=Entry(nice_name(path),emulators['eden']['command']+['-f','-g',str(path)],'emulated','Switch',str(path),mods=True);found[e.id]=e
    # Quiver has already selected the executable: don't substitute a setup AppImage.
    from .installations import launcher_roots,apps_folder,is_launcher_root
    for root in launcher_roots(home,preferences):
        apps=apps_folder(root)
        for folder in apps.glob('*'):
            if not folder.is_dir():continue
            choice=folder/'selected_executable.txt'
            try:
                if choice.exists():
                    exe=pathlib.Path(choice.read_text().strip())
                    if not exe.is_absolute():exe=choice.parent/exe
                else:
                    candidates=[p for p in folder.iterdir() if p.is_file() and (p.suffix.lower()=='.appimage' or p.name.lower() in ('launch.sh','run.sh','start.sh')) and not any(word in p.name.lower() for word in ('setup','install','update','uninstall'))]
                    if len(candidates)!=1:
                        from .ports import find_executable
                        guessed=find_executable(folder);candidates=[guessed] if guessed else []
                    if len(candidates)!=1:continue
                    exe=candidates[0]
                if not exe.is_file():continue
                name=choice.parent.name.split('-')[0]; name=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',name)
                if 'MarioKartWii' in choice.parent.name:name='Mario Kart Wii'
                e=Entry(name,[str(exe)],'port','Linux',str(exe),str(choice.parent)); found[e.id]=e
            except OSError:continue
    # A registered WiiCompiled product takes precedence over the Quiver setup wrapper.
    for data in wiicompiled_roots(home,preferences):
        binary=data/'Install/Base/WiiCompiled'
        state=data/'install-state.json'
        if state.exists():
            try:
                product=next((p for p in json.loads(state.read_text()).get('Products',[]) if p.get('Profile')=='base'),{})
                if product:binary=pathlib.Path(product['InstallDirectory'])/product.get('ExecutableName','WiiCompiled')
            except (OSError,ValueError,KeyError):pass
        if binary.is_file():
            found={k:v for k,v in found.items() if not (v.name=='Mario Kart Wii' and v.platform=='Linux')}
            is_flatpak='.var/app/io.github.TeamWheelWizard.WheelWizard/' in str(data)
            command=['/usr/bin/flatpak','run','--filesystem=home','--command='+str(binary),'io.github.TeamWheelWizard.WheelWizard'] if is_flatpak else [str(binary)]
            extra={}
            manifest=data/'deck-library-install.json'
            if manifest.exists():
                extra=json.loads(manifest.read_text())
                if extra.get('sdk')=='org.kde.Sdk//6.11':command=['/usr/bin/flatpak','run','--socket=x11','--socket=wayland','--socket=pulseaudio','--device=dri','--share=ipc','--filesystem=home','--env=XDG_DATA_HOME='+extra['data_home'],'--command='+str(binary),extra['sdk']]
            e=Entry('Mario Kart Wii',command,'wiicompiled','WiiCompiled',str(binary),str(binary.parent),game_id='RMCP01',metadata={'adapter':'wiicompiled','config':str(data/'Config.toml'),'data_root':str(data),'build':'0.2.33' if is_flatpak else '',**extra});found[e.id]=e
    # Conservative port discovery: executable top-level launchers only, never setup tools.
    for ports in dict.fromkeys([home/'ports',*map(pathlib.Path,preferences.get('port_roots',[]))]):
      if ports.is_dir():
        for folder in ports.iterdir():
            if not folder.is_dir() or folder.name in ('quiver-launcher','steamdeck-tools','deck-library') or is_launcher_root(folder):continue
            from .ports import entries_for as installed_ports
            managed=installed_ports(folder)
            if managed:
                for item in managed:found[item.id]=item
                continue
            candidates=[p for p in folder.iterdir() if p.is_file() and (p.suffix.lower()=='.appimage' or p.name.lower() in ('launch.sh','start.sh','run.sh')) and os.access(p,os.X_OK) and not re.search(r'setup|install|uninstall',p.name,re.I)]
            if len(candidates)==1:
                path=candidates[0]; e=Entry(folder.name.replace('-',' ').title(),[str(path)],'port','Linux',str(path)); found[e.id]=e
    from .project2099 import discover as discover_project2099
    for e in discover_project2099(home,preferences):found[e.id]=e
    for e in prism_entries(home,preferences):found[e.id]=e
    for e in found.values():
        if e.platform=='Switch':e.game_id=switch_id(e);e.metadata['adapter']='eden'
    return sorted(found.values(),key=lambda e:e.name.casefold())
