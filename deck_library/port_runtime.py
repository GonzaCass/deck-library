"""Launch a managed portable Windows port with its own persistent Proton prefix."""
import argparse,json,pathlib,subprocess,sys
from . import project2099
from .models import Store

def command_for(folder,store=None):
    store=store or Store();folder=pathlib.Path(folder).resolve()
    record=json.loads((folder/'.deck-library-port.json').read_text())
    exe=(folder/record['executable']).resolve()
    if not exe.is_relative_to(folder) or not exe.is_file() or exe.suffix.lower()!='.exe':raise ValueError('No se encuentra el ejecutable Windows del port.')
    from .ports import port_id
    prefix=store.root/'runtimes/ports'/port_id(record['repository']);prefix.mkdir(parents=True,exist_ok=True)
    env=project2099.proton_env(store);env['STEAM_COMPAT_DATA_PATH']=str(prefix)
    args=record.get('args',[])
    if record['repository'].lower()=='florinp93/hells-gate-recomp':
        from .dante import arguments
        args=arguments(folder)
    return [str(project2099.proton_path()),'run',str(exe),*args],env

def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder');args=parser.parse_args()
    command,env=command_for(args.folder)
    return subprocess.call(command,cwd=pathlib.Path(command[2]).parent,env=env)

if __name__=='__main__':sys.exit(main())
