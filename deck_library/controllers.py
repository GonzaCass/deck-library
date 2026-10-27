"""Steam Input templates per controller family, so non-Steam shortcuts get a gamepad layout.

Steam stores the layout chosen for a shortcut in one `configset_controller_<family>.vdf`
per controller family. A shortcut with no entry in the family's file falls back to a
desktop/browser layout, which exposes no XInput device to the game. That is what happens
when a DualSense is connected to a shortcut that only has an entry for the Deck itself.
"""
import datetime,os,pathlib,re,tempfile
from .steam import steam_running,SteamRunningError
from .steam_input import parse_text

FAMILIES=('neptune','ps5','ps4','ps3','switch_pro','xboxone','xbox360','generic')
TEMPLATE='controller_{}_gamepad_joystick.vdf'
FAMILY_NAMES={'neptune':'Steam Deck','ps5':'DualSense','ps4':'DualShock 4','ps3':'DualShock 3','switch_pro':'Switch Pro','xboxone':'Xbox One / Series','xbox360':'Xbox 360','generic':'Genérico'}

def keys_for(appid):
    """Steam writes both the unsigned and the signed form of a shortcut ID."""
    unsigned=int(appid)&0xffffffff
    signed=unsigned-(1<<32) if unsigned>=1<<31 else unsigned
    return [str(unsigned)]+([str(signed)] if signed!=unsigned else [])

def config_dir(account):
    """Folder holding the configsets for an account's `userdata/<id>/config` path."""
    account=pathlib.Path(account)
    return account.parent.parent.parent/'steamapps/common/Steam Controller Configs'/account.parent.name/'config'

def templates_dir(account):
    return pathlib.Path(account).parent.parent.parent/'controller_base/templates'

SCREENS_TEMPLATE='controller_neptune_deck_library_screens.vdf'
SCREEN_BUTTONS=(('button_back_left','F9'),('button_back_right','F10'))

def screens_template(account):
    """Steam Deck layout for dual-screen games: the stock gamepad layout plus L4 = F9 (swap screens) and R4 = F10 (change layout).

    The file is a copy of the stock template next to it, so Steam keeps its own templates untouched. Returns its name.
    """
    folder=templates_dir(account);base=folder/TEMPLATE.format('neptune')
    text=base.read_text(encoding='utf-8')
    for name,key in SCREEN_BUTTONS:
        pattern=re.compile(r'("'+name+r'"\s*\{\s*"activators"\s*\{\s*"Full_Press"\s*\{\s*"bindings"\s*\{)(\s*)\}')
        text,count=pattern.subn(lambda m:m[1]+'\n\t\t\t\t\t\t\t"binding"\t\t"key_press '+key+'"\n\t\t\t\t\t\t}',text,count=1)
        if not count:raise ValueError('La plantilla de Steam no tiene el botón '+name+' libre.')
    target=folder/SCREENS_TEMPLATE
    if not target.is_file() or target.read_text(encoding='utf-8')!=text:target.write_text(text,encoding='utf-8')
    return SCREENS_TEMPLATE

def families_available(account):
    """Families whose joystick template exists in this Steam installation."""
    folder=templates_dir(account)
    return [f for f in FAMILIES if (folder/TEMPLATE.format(f)).is_file()]

def read_configset(path):
    path=pathlib.Path(path)
    if not path.is_file():return []
    root=dict(parse_text(path.read_text())).get('controller_config',[])
    if not isinstance(root,list):raise ValueError('Archivo de controles de Steam no reconocido.')
    return root

def render(pairs,root='controller_config'):
    def escape(value):return value.replace('\\','\\\\').replace('"','\\"')
    def block(items,depth):
        pad='\t'*depth;out=[]
        for key,value in items:
            if isinstance(value,list):out.append(f'{pad}"{escape(key)}"\n{pad}{{\n'+block(value,depth+1)+f'{pad}}}\n')
            else:out.append(f'{pad}"{escape(key)}"\t\t"{escape(value)}"\n')
        return ''.join(out)
    return '"'+root+'"\n{\n'+block(pairs,1)+'}\n'

def write_configset(path,pairs,old_text=None):
    """Atomic write; the previous file is kept next to it."""
    path=pathlib.Path(path);backup=None
    if path.is_file():
        old=path.read_text() if old_text is None else old_text
        stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backup=path.with_name(path.name+'.deck-library-backup-'+stamp);backup.write_text(old)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.configset-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as out:out.write(render(pairs));out.flush();os.fsync(out.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return backup

def apply(account,appids,force=False,families=None,is_running=None,special=(),library=()):
    """Assign the gamepad template to each shortcut. Existing choices are kept unless `force`."""
    is_running=is_running or steam_running
    if is_running():raise SteamRunningError('Steam debe estar cerrado para guardar los controles.')
    folder=config_dir(account);available=families_available(account)
    families=[f for f in (families or FAMILIES) if f in available]
    special={int(a)&0xffffffff for a in special};library={int(a)&0xffffffff for a in library};changed=[];backups=[]
    for family in families:
        path=folder/f'configset_controller_{family}.vdf'
        pairs=read_configset(path);present={key:index for index,(key,_) in enumerate(pairs)};dirty=False
        for appid in appids:
            for key in keys_for(appid):
                chosen=library_template(account) if family=='neptune' and int(appid)&0xffffffff in library else screens_template(account) if family=='neptune' and int(appid)&0xffffffff in special else TEMPLATE.format(family)
                entry=[('template',chosen)]
                if key in present:
                    index=present[key]
                    if not force or dict(pairs[index][1]).get('template')==entry[0][1]:continue
                    pairs[index]=(key,entry)
                else:pairs.append((key,entry));present[key]=len(pairs)-1
                dirty=True;changed.append((family,key))
        if dirty:
            if is_running():raise SteamRunningError('Steam se abrió durante el guardado de los controles.')
            backup=write_configset(path,pairs)
            if backup:backups.append(str(backup))
    return {'changed':len(changed),'families':sorted({f for f,_ in changed}),'backups':backups}

def forget(account,appids,is_running=None):
    """Drop the layout choice of removed shortcuts from every family file."""
    is_running=is_running or steam_running
    if is_running():raise SteamRunningError('Steam debe estar cerrado para guardar los controles.')
    folder=config_dir(account)
    if not folder.is_dir():return 0
    wanted={k for appid in appids for k in keys_for(appid)};removed=0
    for path in sorted(folder.glob('configset_controller_*.vdf')):
        pairs=read_configset(path);kept=[(k,v) for k,v in pairs if k not in wanted]
        if len(kept)!=len(pairs):removed+=len(pairs)-len(kept);write_configset(path,kept)
    return removed

def status(account,appid):
    """Per-family state of one shortcut: the template name, 'other' for saved layouts, or None."""
    folder=config_dir(account);result={}
    for family in families_available(account):
        try:pairs=dict(read_configset(folder/f'configset_controller_{family}.vdf'))
        except (OSError,ValueError):pairs={}
        entry=next((pairs[k] for k in keys_for(appid) if k in pairs),None)
        result[family]=None if entry is None else (dict(entry).get('template') or 'other') if isinstance(entry,list) else 'other'
    return result


LIBRARY_TEMPLATE='controller_neptune_deck_library_ui.vdf'

def library_mapping(text):
    """Native gamepad sticks/buttons plus a mouse on the right trackpad only."""
    from .steam_input import first
    document=parse_text(text);mapping=first(document,'controller_mappings',None)
    if not isinstance(mapping,list):raise ValueError('Plantilla de mando de Steam no reconocida.')
    groups=[value for key,value in mapping if key=='group' and isinstance(value,list)]
    identifier=str(max([int(first(group,'id','0')) for group in groups]+[-1])+1)
    mouse=[('id',identifier),('mode','absolute_mouse'),('inputs',[('click',[('activators',[('Soft_Press',[('bindings',[('binding','mouse_button LEFT')])])])])]),('settings',[('sensitivity','145')])]
    mapping.append(('group',mouse))
    for key,value in mapping:
        if key!='preset' or not isinstance(value,list):continue
        for name,bindings in value:
            if name=='group_source_bindings' and isinstance(bindings,list):
                bindings[:]=[(k,v) for k,v in bindings if not isinstance(v,str) or not v.startswith('right_trackpad ')]
                bindings.append((identifier,'right_trackpad active'))
    for key,value in [('title','Deck Library'),('description','Stick izquierdo: navegar. Stick derecho: desplazar. A: seleccionar. B: volver. Trackpad derecho: ratón.'),('revision','2')]:
        mapping[:]=[(k,v) for k,v in mapping if k!=key];mapping.append((key,value))
    return render(mapping,root='controller_mappings')

def library_template(account):
    """Refresh only our owned template; never change a chosen layout/configset here."""
    folder=templates_dir(account);text=library_mapping((folder/TEMPLATE.format('neptune')).read_text(encoding='utf-8-sig'))
    target=folder/LIBRARY_TEMPLATE
    if not target.exists() or target.read_text(encoding='utf-8')!=text:
        if target.exists():
            stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backup=target.with_name(target.name+'.deck-library-backup-'+stamp);backup.write_bytes(target.read_bytes());backup.chmod(0o600)
        fd,temp=tempfile.mkstemp(prefix='.deck-library-template-',dir=folder)
        try:
            with os.fdopen(fd,'w') as out:out.write(text);out.flush();os.fsync(out.fileno())
            os.replace(temp,target)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    return LIBRARY_TEMPLATE
