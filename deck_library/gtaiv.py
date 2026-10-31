"""Pinned GTA IV Complete Edition recipe; never starts the game or edits saves."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import re
import struct
import tempfile
import urllib.request
import zipfile
from .models import Entry, Store, atomic_json

URL = 'https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/releases/download/v4.0.5/GTAIV.EFLC.FusionFix.zip'
SHA256 = 'd78abf54aaf86a8193278a77bafc33dbc7767bd57d80968a8ed42edd75ba06bd'
LATEST_VERSION = '5.1.2'
LATEST_SHA256 = '138f4067a2d2f09df2df80c4378407ad7c742be0e3b99f090633d50820bb2450'
DXVK = 'd3d9.maxFrameLatency = 1\nd3d9.presentInterval = 1\n'
REMOVED = {
    'update/TBoGT/common/data/carcols.dat', 'update/TBoGT/common/data/fonts.dat',
    'update/TBoGT/pc/models/cdimages/playerped.rpf',
    'update/TLAD/pc/models/cdimages/playerped.rpf', 'update/common/data/visualsettings.dat',
}
CFG = 'plugins/GTAIV.EFLC.FusionFix.cfg'
INI = 'plugins/GTAIV.EFLC.FusionFix.ini'

def digest(path):
    if not path.exists(): return None
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def busy(proc=pathlib.Path('/proc')):
    for path in proc.glob('[0-9]*/cmdline'):
        try:
            name=path.read_bytes().split(b'\0')[0].replace(b'\\', b'/').rsplit(b'/',1)[-1].lower()
            if name in (b'gtaiv.exe', b'eflc.exe'): return True
        except OSError: pass
    return False

def check_closed():
    if busy(): raise RuntimeError('GTA IV debe estar cerrado para aplicar o restaurar el arreglo.')

def version(root):
    data=(root/'GTAIV.exe').read_bytes()
    offset=data.find(b'\xbd\x04\xef\xfe')
    if not data.startswith(b'MZ') or offset<0: raise ValueError('No se reconoce la versión de GTAIV.exe.')
    high,low=struct.unpack_from('<II',data,offset+8)
    return '.'.join(map(str,(high>>16,high&65535,low>>16,low&65535)))

def validate_root(root):
    root=pathlib.Path(root).resolve()
    if version(root)!='1.2.0.59':
        raise ValueError('Este arreglo está validado para GTA IV Complete Edition 1.2.0.59; no se modificó otra versión.')
    return root

def safe_target(root,name):
    path=pathlib.PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError('Ruta de paquete inválida.')
    target=root/path
    for part in (target,*target.parents):
        if part==root: break
        if part.is_symlink(): raise ValueError('El destino contiene un enlace simbólico: '+str(part))
    if target.exists() and not target.is_file(): raise ValueError('El destino no es un archivo: '+str(target))
    return target

def discover(home=None):
    home=pathlib.Path(home or pathlib.Path.home())
    roots=[home/'.local/share/Steam',home/'.steam/steam',home/'.var/app/com.valvesoftware.Steam/data/Steam']
    libraries=set()
    for root in roots:
        if not root.exists(): continue
        libraries.add(root.resolve())
        vdf=root/'steamapps/libraryfolders.vdf'
        if vdf.exists():
            for value in re.findall(r'"path"\s+"([^"\n]+)"',vdf.read_text()):
                libraries.add(pathlib.Path(value.replace('\\\\','\\')).resolve())
    for library in sorted(libraries):
        manifest=library/'steamapps/appmanifest_12210.acf'
        if not manifest.exists(): continue
        match=re.search(r'"installdir"\s+"([^"\n]+)"',manifest.read_text())
        if not match or '/' in match[1] or '\\' in match[1] or match[1] in ('.','..'): continue
        game=library/'steamapps/common'/match[1]/'GTAIV'
        if not (game/'GTAIV.exe').is_file(): continue
        settings=[]
        for steam in [library,*roots]:
            folder=steam/'steamapps/compatdata/12210/pfx/drive_c/users/steamuser/AppData/Local/Rockstar Games/GTA IV/Settings/SETTINGS.CFG'
            if folder.is_file() and folder.resolve() not in settings: settings.append(folder.resolve())
        entry=Entry('Grand Theft Auto IV',['steam','steam://run/12210'],'steam','Windows',str(game),game_id='12210',metadata={'steam_appid':12210,'steam_store':True,'gtaiv_root':str(game),'gtaiv_settings':str(settings[0]) if len(settings)==1 else ''})
        return [entry]
    return []

def recipe(release):
    if release=='4.0.5':return URL,SHA256
    if release==LATEST_VERSION:return 'https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/releases/download/v'+release+'/GTAIV.EFLC.FusionFix.zip',LATEST_SHA256
    raise ValueError('Versión de FusionFix no admitida.')

def download(store,release='4.0.5'):
    url,checksum=recipe(release)
    path=store.root/('downloads/fusionfix-'+release+'.zip')
    if path.exists() and digest(path)==checksum: return path
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.fusionfix-')
    try:
        with os.fdopen(fd,'wb') as out, urllib.request.urlopen(url,timeout=60) as response:
            if not response.url.startswith('https://'): raise ValueError('Descarga sin HTTPS.')
            size=0
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>250*1024*1024: raise ValueError('Paquete demasiado grande.')
                out.write(chunk)
        if digest(pathlib.Path(name))!=checksum: raise ValueError('La descarga no coincide con el SHA-256 fijado.')
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)
    return path

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.gtaiv-')
    try:
        with os.fdopen(fd,'wb') as out: out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def patch_ini(text,updates):
    """Preserve unknown settings/comments while replacing only requested keys."""
    section='';out=[];remaining={s:dict(v) for s,v in updates.items()}
    def append_missing():
        for k,v in remaining.get(section,{}).items(): out.append(k+' = '+str(v))
        remaining.pop(section,None)
    for line in text.splitlines():
        match=re.match(r'^\s*\[([^]]+)\]',line)
        if match: append_missing(); section=match[1]
        key=re.match(r'^\s*([^=]+?)\s*=',line)
        if key and key[1] in remaining.get(section,{}):
            line=key[1]+' = '+str(remaining[section].pop(key[1]))
        out.append(line)
    append_missing()
    for section,values in remaining.items():
        out.extend(['','['+section+']',*[k+' = '+str(v) for k,v in values.items()]])
    return '\n'.join(out)+'\n'

def state_path(root,store):
    key=hashlib.sha256(str(root).encode()).hexdigest()[:20]
    return store.root/'gtaiv'/key

def installed_release(root,store=None):
    store=store or Store();root=pathlib.Path(root).resolve()
    try:
        state=state_path(root,store);backup=pathlib.Path(json.loads((state/'last.json').read_text())['backup'])
        record=json.loads((backup/'record.json').read_text())
        row=next(r for r in record['files'] if r['name']=='plugins/GTAIV.EFLC.FusionFix.asi')
        if digest(root/row['name'])==row['after'] and record['version'] in ('4.0.5',LATEST_VERSION):return record['version']
    except (OSError,ValueError,KeyError,StopIteration):pass
    return ''

def apply(root,settings,store=None,archive=None,release='4.0.5'):
    _,checksum=recipe(release)
    store=store or Store();root=validate_root(root);check_closed()
    settings=pathlib.Path(settings)
    if settings.is_symlink(): raise ValueError('La configuración no debe ser un enlace simbólico.')
    settings=settings.resolve()
    before=settings.read_bytes()
    if len(before)!=1469 or before[:4]!=b'\x12\x15\x28\x10' or struct.unpack_from('<I',before,608)[0] not in (0,1):
        raise ValueError('Formato de SETTINGS.CFG no reconocido; no se modificó.')
    archive=pathlib.Path(archive) if archive else download(store,release)
    if digest(archive)!=checksum: raise ValueError('El paquete no coincide con FusionFix '+release+' oficial.')
    state=state_path(root,store);state.mkdir(parents=True,exist_ok=True)
    with (state/'lock').open('w') as lock, zipfile.ZipFile(archive) as package:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        names={i.filename for i in package.infolist() if not i.is_dir()}
        if not {INI,'plugins/GTAIV.EFLC.FusionFix.asi','vulkan.dll','d3d9.dll','dinput8.dll'}<=names or package.testzip():
            raise ValueError('El paquete está incompleto o dañado.')
        targets={n:safe_target(root,n) for n in names|REMOVED|{CFG,'dxvk.conf','d3d9.cfg'}}
        targets['SETTINGS.CFG']=settings
        if settings in [p for n,p in targets.items() if n!='SETTINGS.CFG']: raise ValueError('Ruta de ajustes inválida.')
        initial={n:digest(p) for n,p in targets.items()}
        if digest(settings)!=hashlib.sha256(before).hexdigest():raise RuntimeError('La configuración cambió durante la descarga.')
        changes={n:package.read(n) for n in names}
        # Merge only keys present in the selected release's INI template.
        old=targets[INI].read_text() if targets[INI].exists() else ''
        section='';values={}
        for line in old.splitlines():
            line=line.split('//',1)[0].strip()
            if line.startswith('['): section=line[1:].split(']',1)[0]
            elif '=' in line:
                k,v=line.split('=',1);values.setdefault(section,{})[k.strip()]=v.strip()
        template=changes[INI].decode();known={};section=''
        for line in template.splitlines():
            if line.startswith('['):section=line[1:].split(']',1)[0]
            elif '=' in line:
                k=line.split('=',1)[0].strip()
                if k in values.get(section,{}) and k!='CustomUserProfilePath':known.setdefault(section,{})[k]=values[section][k]
        # Preserve a private custom profile path locally; never export it.
        if values.get('USERPROFILE',{}).get('CustomUserProfilePath'):
            known.setdefault('USERPROFILE',{})['CustomUserProfilePath']=values['USERPROFILE']['CustomUserProfilePath']
        changes[INI]=patch_ini(template,known).encode()
        cfg=targets[CFG].read_text() if targets[CFG].exists() else '[FRAMELIMIT]\nFpsLimitPreset = 7\n'
        if release==LATEST_VERSION:
            # 5.1.2 stores zero-based enums; older CFG values are menu IDs.
            # Start a new menu CFG rather than interpreting those IDs as enum values.
            # Values below are pinned to source/settings.ixx at tag v5.1.2.
            changes[CFG]=patch_ini('',{'MAIN':{'GraphicsAPI':1,'Windowed':0,'Bloom':0,'Definition':1},'FRAMELIMIT':{'FpsLimitPreset':5},'MISC':{'Buttons':4,'Antialiasing':2,'SunShafts':0,'AmbientOcclusion':0,'ScreenFilter':1},'FOG':{'VolumetricFog':0},'SHADOWS':{'ShadowFilter':1},'UPDATE':{'CheckForUpdates':0}}).encode()
            language=re.search(r'(?ms)^\[LANGUAGEOVERRIDE\]\s*.*?^Language\s*=\s*(\d+)\s*$',cfg)
            if language:changes[CFG]=patch_ini(changes[CFG].decode(),{'LANGUAGEOVERRIDE':{'Language':language[1]}}).encode()
        else:changes[CFG]=patch_ini(cfg,{'MAIN':{'GraphicsAPI':1},'MISC':{'Buttons':9},'UPDATE':{'CheckForUpdates':0}}).encode()
        changes['d3d9.cfg']=patch_ini(targets['d3d9.cfg'].read_text() if targets['d3d9.cfg'].exists() else '',{'MAIN':{'API':1}}).encode()
        # Keep unrelated DXVK options; overwrite just the two confirmed options.
        text=targets['dxvk.conf'].read_text() if targets['dxvk.conf'].exists() else ''
        text=re.sub(r'(?m)^\s*d3d9\.(maxFrameLatency|presentInterval)\s*=.*\n?', '',text)
        changes['dxvk.conf']=(text.rstrip()+'\n'+DXVK).lstrip().encode()
        new=bytearray(before);struct.pack_into('<I',new,608,0);changes['SETTINGS.CFG']=bytes(new)
        changes.update({n:None for n in REMOVED-names})
        check_closed()
        backup=state/datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backup.mkdir()
        record={'root':str(root),'version':release,'files':[]}
        for n,p in targets.items():
            original=p.read_bytes() if p.exists() else None
            if (hashlib.sha256(original).hexdigest() if original is not None else None)!=initial[n]:
                raise RuntimeError('Un archivo cambió mientras se preparaba el arreglo.')
            record['files'].append({'name':n,'target':str(p),'before':hashlib.sha256(original).hexdigest() if original is not None else None,'after':hashlib.sha256(changes[n]).hexdigest() if changes[n] is not None else None})
            if original is not None: write(backup/'files'/n,original)
        atomic_json(backup/'record.json',record)
        try:
            for n,p in targets.items():
                if digest(p)!=next(r['before'] for r in record['files'] if r['name']==n): raise RuntimeError('Un archivo cambió durante la aplicación.')
            check_closed()
            for n,p in targets.items():
                if changes[n] is None: p.unlink(missing_ok=True)
                else: write(p,changes[n])
            for r in record['files']:
                if digest(pathlib.Path(r['target']))!=r['after']: raise RuntimeError('La verificación del archivo falló.')
            atomic_json(state/'last.json',{'backup':str(backup)})
        except Exception:
            for r in record['files']:
                p=pathlib.Path(r['target'])
                if r['before'] is None:p.unlink(missing_ok=True)
                else:write(p,(backup/'files'/r['name']).read_bytes())
            raise
    return str(backup)

def remove_color_filter(root,store=None):
    """5.1.2: default=0, OFF=1. Back up only the menu CFG, keeping FPS and graphics."""
    store=store or Store();root=validate_root(root);check_closed()
    if installed_release(root,store)!=LATEST_VERSION:
        raise ValueError('Este cambio necesita la instalación de FusionFix 5.1.2 registrada por Deck Library.')
    state=state_path(root,store)
    with (state/'lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=safe_target(root,CFG);before=path.read_bytes()
        changed=patch_ini(before.decode(),{'MISC':{'ScreenFilter':1}}).encode()
        backup=state/('color-filter-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f'))
        write(backup/'files'/CFG,before)
        atomic_json(backup/'record.json',{'version':LATEST_VERSION,'files':[{'name':CFG,'before':hashlib.sha256(before).hexdigest(),'after':hashlib.sha256(changed).hexdigest()}]})
        check_closed()
        if path.read_bytes()!=before:raise RuntimeError('La configuración cambió. Volver a comprobarla.')
        write(path,changed)
    return str(backup)

def restore(root,store=None,preserve_current_settings=False):
    store=store or Store();root=pathlib.Path(root).resolve();check_closed();state=state_path(root,store)
    with (state/'lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        backup=pathlib.Path(json.loads((state/'last.json').read_text())['backup'])
        record=json.loads((backup/'record.json').read_text())
        changed_settings=[]
        for r in record['files']:
            p=pathlib.Path(r['target'])
            if r['name']!='SETTINGS.CFG':safe_target(root,r['name'])
            if p.is_symlink():raise ValueError('La configuración no debe ser un enlace simbólico.')
            if digest(p)!=r['after']:
                if preserve_current_settings and r['name'] in {CFG,INI,'SETTINGS.CFG','d3d9.cfg','dxvk.conf'}:
                    changed_settings.append((r,p.read_bytes() if p.is_file() else None))
                else:raise ValueError('Hay cambios posteriores en '+r['name']+'. Se conserva el respaldo sin sobrescribirlos.')
            if r['before'] is not None and digest(backup/'files'/r['name'])!=r['before']:raise ValueError('Respaldo dañado.')
        if changed_settings:
            saved=state/('before-restore-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f'))
            for r,data in changed_settings:
                if data is not None:write(saved/'files'/r['name'],data)
            atomic_json(saved/'record.json',{'restoring':str(backup),'files':[{'name':r['name'],'present':data is not None} for r,data in changed_settings]})
        check_closed()
        for r in record['files']:
            p=pathlib.Path(r['target'])
            if r['before'] is None:p.unlink(missing_ok=True)
            else:write(p,(backup/'files'/r['name']).read_bytes())
        (state/'last.json').unlink()
    return str(backup)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['detect','apply','restore'])
    parser.add_argument('--root',type=pathlib.Path)
    parser.add_argument('--settings',type=pathlib.Path)
    parser.add_argument('--archive',type=pathlib.Path)
    parser.add_argument('--release',choices=['4.0.5',LATEST_VERSION],default='4.0.5')
    args=parser.parse_args()
    if args.action=='detect': print(json.dumps([e.to_dict() for e in discover()],indent=2));return
    if args.root is None:parser.error('Falta --root.')
    if args.action=='apply' and args.settings is None:parser.error('Falta --settings.')
    print(apply(args.root,args.settings,archive=args.archive,release=args.release) if args.action=='apply' else restore(args.root))

if __name__=='__main__':main()
