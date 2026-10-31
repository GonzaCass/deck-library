"""Recover missing ROM references without deleting original files or emulator data."""
import pathlib
from .models import Entry,atomic_json


def extensions(entry):
    from .discovery import SYSTEMS
    return set().union(*(row[3] for row in SYSTEMS.values() if row[0]==entry.platform))


def missing(entries,preferences=None):
    preferences=preferences or {}
    hidden=set(preferences.get('hidden_entries',[]))|set(preferences.get('hidden_originals',[]))
    return [e for e in entries if e.kind=='emulated' and e.id not in hidden and e.source
            and pathlib.Path(e.source).is_absolute() and not pathlib.Path(e.source).is_file()]


def forgotten(store):
    import json
    path=store.root/'removed-roms.json'
    if not path.exists():return []
    value=json.loads(path.read_text())
    if not isinstance(value,list):raise ValueError('El registro de ROMs quitadas no es válido.')
    return value


def ignored_shortcuts(store):
    # Keep a still-open Steam session from importing a shortcut queued for removal.
    return {(str(r['account']),r['appid']) for r in forgotten(store) if r.get('account') and r.get('appid') is not None and not pathlib.Path(r['source']).is_file()}


def filter_forgotten(entries,store):
    records=forgotten(store)
    return [e for e in entries if not any(e.id==r['id'] and not pathlib.Path(r['source']).is_file() for r in records)]


def relocate(entry,path,store,start_worker=True):
    from .service import queue_entries
    from .runtime import make_launcher
    target=pathlib.Path(path).expanduser().resolve(strict=True)
    allowed=extensions(entry)
    if not target.is_file() or target.stat().st_size==0 or (allowed and target.suffix.lower() not in allowed):
        raise ValueError('Elegir una ROM compatible con la plataforma del juego.')
    # Switch IDs can be checked without reading/decrypting an entire ROM.
    if entry.platform=='Switch' and entry.game_id:
        from .content import switch_id
        detected=switch_id(Entry(target.stem,['rom',str(target)],kind='emulated',platform='Switch',source=str(target)))
        if detected and detected.casefold()!=entry.game_id.casefold():raise ValueError('El archivo elegido corresponde a otro juego de Switch.')
    entries=store.load()
    current=next((e for e in entries if e.id==entry.id),None)
    if current is None:raise ValueError('El juego ya no está en la biblioteca.')
    if current.source!=entry.source:raise ValueError('La ubicación cambió durante la selección. Volver a comprobarla.')
    duplicates=[e for e in entries if e.id!=entry.id and e.kind=='emulated' and e.platform==entry.platform and pathlib.Path(e.source)==target]
    if any(e.metadata.get('steam_appid') is not None for e in duplicates):
        raise ValueError('Esa ROM ya tiene otro acceso de Steam en la biblioteca. Quitar o desvincular el duplicado antes de cambiar la ubicación.')
    fresh=Entry.from_dict(current.to_dict());old=current.source
    replaced=False;command=[]
    for arg in current.command:
        if arg==old:arg=str(target);replaced=True
        elif arg.endswith('='+old):arg=arg[:-len(old)]+str(target);replaced=True
        command.append(arg)
    if not replaced:raise ValueError('El comando es personalizado y no contiene la ruta anterior. Editarlo antes de cambiar la ubicación.')
    fresh.command=command;fresh.source=str(target)
    if fresh.cwd==str(pathlib.Path(old).parent):fresh.cwd=str(target.parent)
    if fresh.metadata.get('original_source')==old:fresh.metadata['original_source']=str(target)
    updated=[fresh if e.id==entry.id else e for e in entries if e not in duplicates]
    store.save(updated)
    # Existing managed shortcuts read the library by ID; direct shortcuts need updating.
    account=fresh.metadata.get('steam_account');appid=fresh.metadata.get('steam_appid')
    if account and appid is not None:
        from .steam_inventory import shortcuts,launch_command
        item=next((s for s in shortcuts(pathlib.Path(account)) if s['appid']==appid),None)
        launcher=str(store.root/'launchers'/(fresh.id+'.sh'))
        try:
            make_launcher(fresh,store)
            if item and launch_command(item)[0]!=launcher:queue_entries([fresh],pathlib.Path(account),store,start_worker=start_worker)
        except Exception:
            store.save(entries);raise
    return fresh


def forget(entry,store,start_worker=True):
    from .port_removal import prepare_steam
    entries=store.load();current=next((e for e in entries if e.id==entry.id),None)
    if current is None:return {'state':'idle'}
    if pathlib.Path(current.source).is_file():raise ValueError('La ROM volvió a estar disponible. No se quitó el juego.')
    account=current.metadata.get('steam_account');appid=current.metadata.get('steam_appid')
    if account and appid is not None and any(e.id!=current.id and e.metadata.get('steam_account')==account and e.metadata.get('steam_appid')==appid for e in entries):
        raise ValueError('Otro juego comparte ese acceso de Steam. Desvincularlo antes de quitarlo.')
    records=forgotten(store)
    record={'id':current.id,'source':current.source,'account':current.metadata.get('steam_account'),'appid':current.metadata.get('steam_appid')}
    # Persist the guard before queuing a removal that may run in another process.
    atomic_json(store.root/'removed-roms.json',[r for r in records if r['id']!=current.id]+[record])
    try:result=prepare_steam({'entries':[current],'ids':[current.id]},store,start_worker=start_worker)
    except Exception:
        atomic_json(store.root/'removed-roms.json',records);raise
    store.save([e for e in entries if e.id!=current.id])
    return result
