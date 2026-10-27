"""Locate installed Proton builds in Steam libraries, including removable storage."""
import pathlib,re
from .steam_input import parse_text,first

def steam_roots(home=None):
    home=pathlib.Path(home or pathlib.Path.home())
    return list(dict.fromkeys((home/p).resolve() for p in ('.local/share/Steam','.steam/steam','.steam/root','.var/app/com.valvesoftware.Steam/data/Steam') if (home/p).is_dir()))

def libraries(home=None):
    roots=steam_roots(home);result=list(roots)
    for root in roots:
        try:
            text=(root/'steamapps/libraryfolders.vdf').read_text()
            if len(text)>2*1024*1024:continue
            for _,value in first(parse_text(text),'libraryfolders',[]):
                path=first(value,'path') if isinstance(value,list) else value
                if isinstance(path,str) and pathlib.Path(path).is_absolute() and pathlib.Path(path).is_dir():result.append(pathlib.Path(path).resolve())
        except (OSError,ValueError,TypeError):pass
    return list(dict.fromkeys(result))

def find(names,home=None,preferred=None):
    roots=libraries(home)
    for name in (preferred,) if preferred else names:
        for root in roots:
            tool=root/'steamapps/common'/name/'proton'
            if tool.is_file():return tool
    if not preferred:
        custom=[]
        for root in steam_roots(home):
            for folder in (root/'compatibilitytools.d').glob('*'):
                if re.match(r'^(?:GE-Proton|Proton-GE)',folder.name,re.I) and (folder/'proton').is_file():custom.append(folder/'proton')
        if custom:return max(custom,key=lambda p:tuple(int(n) for n in re.findall(r'\d+',p.parent.name)))
    raise ValueError('No se encontró Proton instalado. Instalar una versión desde Steam → Biblioteca → Herramientas, o GE-Proton con ProtonUp-Qt.')

def installed(home=None):
    """Installed tools only; preferences store a build name, never an executable path."""
    tools={}
    folders=[root/'steamapps/common' for root in libraries(home)]
    folders.extend(root/'compatibilitytools.d' for root in steam_roots(home))
    for folder in folders:
        for path in folder.glob('*/proton'):
            name=path.parent.name
            if path.is_file() and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,99}',name) and re.match(r'^(?:proton|ge-proton)',name,re.I):tools.setdefault(name,path.resolve())
    return dict(sorted(tools.items(),key=lambda pair:pair[0].casefold()))

def resolve(name,home=None):
    tools=installed(home)
    if name not in tools:raise ValueError('La versión de Proton elegida no está instalada: '+str(name))
    return tools[name]
