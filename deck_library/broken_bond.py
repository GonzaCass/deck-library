"""Steam Deck repair using Auremana's published Broken Bond shader fixes."""
import datetime,json,pathlib,re,shutil,tempfile
from .models import Store,atomic_json

ORIGINAL='jorjbarbosa/broken-bond-recomp'
COMPATIBLE='Auremana666/Naruto-The-Broken-Bond-PC-Port'
FIX='broken-bond-deck-v25'
SETTINGS={'fullscreen':True,'vsync':False,'frame_rate':60,'internal_resolution_scale':1.0,'msaa_samples':1,'transparency_antialiasing':False,'swap_post_effect':'fxaa','upscaling':'cas','input_backend':'sdl','mnk_mode':False,'mnk_mouse':False,'show_title_screen':False}


def status(entry,store=None):
    from . import ports,updates
    repo=entry.metadata.get('port_repository','')
    if repo.casefold()==ORIGINAL:return 'migrate'
    if repo.casefold()!=COMPATIBLE.casefold():return ''
    record=ports.records(store or Store()).get(repo,{})
    if updates.is_newer('2.5',record.get('tag','0')):return 'update'
    return 'applied' if record.get('steam_deck_fix',{}).get('id')==FIX else 'settings'


def defaults(folder,record,force=False):
    """Apply graphics/controller defaults once, retaining user options on later updates."""
    if record['repository'].casefold()!=COMPATIBLE.casefold():return
    if not force and record.get('steam_deck_fix',{}).get('id')==FIX:return
    folder=pathlib.Path(folder);path=folder/'naruto.toml'
    if path.is_symlink():raise ValueError('El archivo de ajustes es un enlace; no se modificó.')
    content=path.read_text() if path.is_file() else ''
    backup=folder/'.deck-library-settings-backups'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
    from .port_removal import safe_path
    safe_path(backup,folder)
    if path.is_file():backup.mkdir(parents=True);shutil.copy2(path,backup/'naruto.toml')
    for key,value in SETTINGS.items():
        line=key+' = '+json.dumps(value);pattern=r'^'+key+r'\s*=.*$'
        if re.search(pattern,content,re.M):content=re.sub(pattern,lambda _:line,content,flags=re.M)
        else:content+='\n'+line
    # Replace atomically so a failed write cannot truncate an existing configuration.
    with tempfile.NamedTemporaryFile('w',dir=folder,delete=False,prefix='.naruto-settings-') as output:
        temporary=pathlib.Path(output.name);output.write(content+'\n')
    try:temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)
    record['steam_deck_fix']={'id':FIX,'settings_version':1}


def repair(entry,store=None,root=None,progress=print,cancel=None,get=None):
    from . import ports,updates,proton_tools
    from .original_data import validate
    from .port_removal import safe_path,in_use
    store=store or Store();root=pathlib.Path(root or ports.ports_root());before=ports.records(store);entries=store.load();repo=entry.metadata.get('port_repository','');record=before.get(repo)
    if not record or not status(entry,store):raise ValueError('Este juego no admite esta reparación.')
    proton_tools.resolve('Proton 11.0')
    if not isinstance(record.get('folder'),str) or not ports.FOLDER.fullmatch(record['folder']):raise ValueError('La carpeta registrada del port no es válida.')
    folder=safe_path(root/record['folder'],root)
    from .port_removal import owns
    if not owns(folder,repo):raise ValueError('No se pudo comprobar que esta carpeta pertenece al port.')
    if in_use([folder]):raise ValueError('Cerrar Broken Bond antes de aplicar la reparación.')
    get=get or ports.fetch_json;backup=None
    if repo.casefold()==ORIGINAL:
        item=ports.clean({'repository':COMPATIBLE,'name':'Naruto: The Broken Bond','category':'Xbox 360'})
        source=validate(safe_path(folder/'game',folder),item['original_data']);target=safe_path(root/item['folder'],root)
        if target.exists():raise ValueError('Ya existe otra instalación del port compatible. No se sobrescribió.')
        release=ports.release_for(COMPATIBLE,get)
        if updates.is_newer('2.5',release.get('tag_name','0')):raise ValueError('La reparación necesita la versión 2.5 o posterior del port compatible.')
        with tempfile.TemporaryDirectory(prefix='.deck-library-fix-',dir=root) as temporary:
            temporary=pathlib.Path(temporary);staging_store=Store(temporary/'state')
            prepared=ports.install(item,staging_store,temporary/'packages',get=lambda _:release,progress=progress,transfer=progress,runtime='proton',cancel=cancel)
            staging=temporary/'packages'/prepared['folder'];prepared.update(entry_id=entry.id,configured=True,configured_with=record.get('configured_with','default.xex'),inputs={'original_data':str(target/'game')})
            if (folder/'user').is_dir():shutil.copytree(folder/'user',staging/'hdd',dirs_exist_ok=True,symlinks=True)
            defaults(staging,prepared)
            manifest=folder/'.deck-library-iso-import.json'
            if manifest.is_file() and not manifest.is_symlink():shutil.copy2(manifest,staging/manifest.name)
            atomic_json(staging/'.deck-library-port.json',prepared);ports.check_cancel(cancel)
            backup=safe_path(root/'.deck-library-replaced'/(record['folder']+'-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')),root);backup.parent.mkdir(exist_ok=True)
            moved=False;promoted=False
            try:
                source.rename(staging/'game');moved=True;folder.rename(backup);staging.rename(target);promoted=True
                replacement=ports.entry_for(target)
                replacement.cover=entry.cover;replacement.icon=entry.icon;replacement.mods=entry.mods
                replacement.metadata={**entry.metadata,**replacement.metadata,'proton_version':'Proton 11.0'}
                after=dict(before);after.pop(repo);after[COMPATIBLE]=prepared;atomic_json(store.root/'ports.json',after)
                store.save([replacement if old.id==entry.id else old for old in entries])
            except BaseException:
                if promoted:target.rename(staging)
                if backup.exists():backup.rename(folder)
                if moved and (staging/'game').exists():(staging/'game').rename(source)
                atomic_json(store.root/'ports.json',before);store.save(entries)
                raise
    else:
        if status(entry,store)=='update':
            configured=record.get('configured',False)
            release=ports.release_for(COMPATIBLE,get)
            if updates.is_newer('2.5',release.get('tag_name','0')):raise ValueError('La reparación necesita la versión 2.5 o posterior del port compatible.')
            record=ports.install(ports.clean(record),store,root,get=lambda _:release,replace=True,runtime='proton',progress=progress,transfer=progress,cancel=cancel)
            record['configured']=configured
        defaults(folder,record,force=True);atomic_json(folder/'.deck-library-port.json',record)
        after=ports.records(store);after[repo]=record;atomic_json(store.root/'ports.json',after)
        replacement=ports.entry_for(folder)
        replacement.cover=entry.cover;replacement.icon=entry.icon;replacement.mods=entry.mods
        replacement.metadata={**entry.metadata,**replacement.metadata,'proton_version':'Proton 11.0'}
        store.save([replacement if old.id==entry.id else old for old in entries])
    state=updates.cached(store)
    for key in ('ports','catalog'):state[key]=[row for row in state.get(key) or [] if row.get('repository','').casefold() not in (ORIGINAL,COMPATIBLE.casefold())]
    atomic_json(updates.cache_path(store),state)
    return {'entry':next(e for e in store.load() if e.id==entry.id),'backup':str(backup) if backup else ''}
