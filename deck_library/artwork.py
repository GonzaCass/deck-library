"""Resolve local artwork, including privately cached provider downloads."""
import pathlib,re
from .steam import find_accounts,read_kv,get

def normalized(name):return re.sub(r'[^a-z0-9]','',re.sub(r'\([^)]*\)|\[[^]]*\]','',name.lower()))

def find_cover(entry,home=None):
    home=pathlib.Path(home or pathlib.Path.home())
    if entry.cover and pathlib.Path(entry.cover).is_file():return entry.cover
    if entry.icon and pathlib.Path(entry.icon).is_file():return entry.icon
    if entry.game_id:
        file=home/'.cache/eden/game_list'/(entry.game_id+'.jpeg')
        if file.exists():return str(file)
    if entry.kind=='wiicompiled':
        for root in (home/'ports/quiver-launcher',home/'Applications/QuiverLauncher'):
            file=root/'Cache/ShortcutIcons/MarioKartWii-MarioKartWiiCompiled_temp.png'
            if file.exists():return str(file)
    wanted=normalized(entry.name)
    for account in find_accounts(home):
        try:
            data=read_kv((account/'shortcuts.vdf').read_bytes())['shortcuts'][1]
            for _,value in data.values():
                if normalized(get(value,'appname',''))!=wanted:continue
                appid=get(value,'appid')
                for suffix in ('p.png','p.jpg','.png','.jpg'):
                    file=account/'grid'/(str(appid)+suffix)
                    if file.exists():return str(file)
        except (OSError,ValueError):pass
    return ''
