"""Launch a managed portable Windows port with its own persistent Proton prefix."""
import argparse,json,pathlib,subprocess,sys,re,time
from . import project2099
from .models import Store

def command_for(folder,store=None,preferred=None):
    store=store or Store();folder=pathlib.Path(folder).resolve()
    from .port_locations import record_at
    record=record_at(folder,store)
    if not record:raise ValueError('No se encuentra el registro del port. Volver a elegir su carpeta desde Deck Library.')
    exe=(folder/record['executable']).resolve()
    if not exe.is_relative_to(folder) or not exe.is_file() or exe.suffix.lower()!='.exe':raise ValueError('No se encuentra el ejecutable Windows del port.')
    from .ports import port_id
    prefix=store.root/'runtimes/ports'/port_id(record['repository']);prefix.mkdir(parents=True,exist_ok=True)
    env=project2099.proton_env(store);env['STEAM_COMPAT_DATA_PATH']=str(prefix)
    args=list(record.get('args',[]))
    if record['repository'].casefold()=='auremana666/naruto-the-broken-bond-pc-port' and (folder/'game/default.xex').is_file() and not any(arg.startswith('--game_data_root') for arg in args):
        args.append('--game_data_root=Z:'+str(folder/'game').replace('/','\\'))
    if record['repository'].lower()=='florinp93/hells-gate-recomp':
        from .dante import arguments
        args=arguments(folder)
    if preferred:
        from .proton_tools import resolve
        tool=resolve(preferred)
    else:tool=project2099.proton_path()
    return [str(tool),'run',str(exe),*args],env

def shader_pending(folder):
    path=pathlib.Path(folder)/'pipeline-guard-pending.txt'
    try:
        if path.is_symlink() or path.stat().st_size>8192:return b''
        value=path.read_bytes().strip()
        return value if re.fullmatch(rb'vs=[0-9a-f]{16} ps=[0-9a-f]{16} w=[0-9a-f,]+',value,re.I) else b''
    except OSError:return b''

def run(command,env,folder,store=None):
    from .port_locations import record_at
    folder=pathlib.Path(folder);record=record_at(folder,store) or {}
    supported=record['repository'].casefold()=='auremana666/naruto-the-broken-bond-pc-port'
    seen=set()
    for attempt in range(7):
        before=shader_pending(folder) if supported else b''
        code=subprocess.call(command,cwd=pathlib.Path(command[2]).parent,env=env)
        if code!=3 or not supported or attempt==6:return code
        pending=shader_pending(folder)
        if not pending or pending==before or pending in seen:return code
        guard=folder/'pipeline-guard.txt'
        try:
            if guard.is_symlink() or guard.stat().st_size>1024*1024:return code
            if pending in (line.strip() for line in guard.read_bytes().splitlines()):return code
        except FileNotFoundError:pass
        except OSError:return code
        seen.add(pending)
        print(f'Shader registrado por el port. Reintentando el inicio ({attempt+1}/6)…',flush=True)
        time.sleep(1)
    return code

def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder');parser.add_argument('--proton');parser.add_argument('--data-dir');args=parser.parse_args()
    command,env=command_for(args.folder,Store(args.data_dir),preferred=args.proton)
    return run(command,env,args.folder,Store(args.data_dir))

if __name__=='__main__':sys.exit(main())
