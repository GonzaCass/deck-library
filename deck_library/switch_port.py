"""Pass selected originals to Savage Wind's own first-run builder, only while needed."""
import os,pathlib

REPOSITORY='revivedx/savagewindrecomp'

def prepared(record,home=None,env=None):
    from .ports import ports_root
    home=pathlib.Path(home or pathlib.Path.home());env=os.environ if env is None else env
    windows=record.get('runtime')=='proton'
    name=record.get('folder')
    if windows and (not isinstance(name,str) or name in ('','.','..') or pathlib.Path(name).name!=name):return False
    data=ports_root(home)/record['folder'] if windows else pathlib.Path(env.get('XDG_DATA_HOME') or home/'.local/share')/'savagewind'
    return all((data/'extracted'/name).is_file() for name in ('exefs/main','romfs.bin','swgame.dll' if windows else 'swgame.so'))

def launch_environment(entry,env,store,home=None):
    if entry.metadata.get('port_repository','').casefold()!=REPOSITORY:return env
    from .ports import records
    record=next((r for repo,r in records(store).items() if repo.casefold()==REPOSITORY),{})
    source=(record.get('inputs') or {}).get('original_data')
    if not source:return env
    windows=record.get('runtime')=='proton'
    # The port validates its own build and version even when these files exist.
    # Never force setup on every launch: doing so would compile again and open its configuration screen.
    if prepared(record,home,env):return env
    from .switch_extract import extracted_folder
    source=extracted_folder(source)
    value=('Z:'+str(source).replace('/','\\')) if windows else str(source)
    return {**env,'SAVAGEWIND_LAUNCHER_SETUP':value,'SAVAGEWIND_LAUNCHER_MODE':'setup'}
