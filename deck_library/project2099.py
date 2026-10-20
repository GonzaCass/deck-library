"""Project-2099 discovery, current official installation and Proton launch."""
import hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile,urllib.request,zipfile
from .models import Entry,Store
from .runtime import clean_environment

VERSION='2.0.0-beta.4.1'
ASSETS={'EOTInstaller-v'+VERSION+'.exe':'526d65eaca119f11b7a8cb5af16ca9a982244c4c5c721051ec8897a9af652043','EOT-PC-Payload-v'+VERSION+'.zip':'91e6d01f91a4e8c4a04e155b9cb5f26c88f99cb96f41bbeec5e3da79b2212fcb'}

def check_image(stream):
    stream.seek(0x8000);header=stream.read(100)
    if b'PS3VOLUME' in header:
        raise ValueError('Esta ISO es de PlayStation 3. Project-2099 necesita Spider-Man: Edge of Time de Xbox 360; no convierte la versión PS3.')
    for offset in (0,0xfb20,0x10600,0x20600,0x2070000,0x2080000,0xfd80000,0xfd90000,0x182f0000,0x18300000):
        stream.seek(offset+32*2048)
        if stream.read(20).startswith(b'MICROSOFT*XBOX*MEDIA'):return
    raise ValueError('No se encontró una imagen Xbox 360 XDVDFS compatible. El instalador oficial valida además los archivos y la revisión del juego.')

def sevenzip_image(path):
    tool=shutil.which('7z') or shutil.which('7zz')
    if not tool:raise ValueError('Falta 7-Zip (7z o 7zz) para abrir este archivo.')
    result=subprocess.run([tool,'l','-slt',str(path)],capture_output=True,text=True,timeout=30)
    if result.returncode:raise ValueError('No se pudo leer el archivo 7z.')
    records=[]
    for block in result.stdout.split('\n\n'):
        fields=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        if fields.get('Path','').lower().endswith('.iso'):
            if fields.get('Encrypted')=='+':raise ValueError('El archivo 7z está cifrado.')
            records.append((fields['Path'],int(fields.get('Size','0'))))
    if len(records)!=1 or records[0][1]<=0:raise ValueError('El 7z debe contener una sola ISO de Xbox 360.')
    return tool,records[0][0],records[0][1]

def validate_source(path):
    path=pathlib.Path(path)
    if path.suffix.lower()=='.7z':
        tool,name,size=sevenzip_image(path)
        process=subprocess.Popen([tool,'e','-so',str(path),name],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        try:
            header=process.stdout.read(0x8000+100)
            if b'PS3VOLUME' in header[0x8000:]:raise ValueError('El 7z contiene una ISO de PlayStation 3. Project-2099 necesita la versión Xbox 360.')
        finally:
            process.stdout.close();process.terminate();process.wait()
        return size
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as z:
            images=[i for i in z.infolist() if i.filename.lower().endswith('.iso')]
            if len(images)!=1:raise ValueError('Se requiere una ISO de Xbox 360 o un ZIP con una sola ISO.')
            # PS3 is rejected after reading only the first 32 KiB, before extraction.
            with z.open(images[0]) as stream:
                stream.seek(0x8000)
                if b'PS3VOLUME' in stream.read(100):
                    raise ValueError('El ZIP contiene una ISO de PlayStation 3. Project-2099 necesita la versión Xbox 360.')
            return images[0].file_size
    with path.open('rb') as stream:check_image(stream)
    return 0

def proton_path(home=None,preferred=None):
    names=('Proton 11.0','Proton - Experimental','Proton 10.0','Proton 9.0 (Beta)','Proton 8.0')
    if preferred and preferred not in names:raise ValueError('Versión de Proton no admitida.')
    home=pathlib.Path(home or pathlib.Path.home())
    for root in (home/'.local/share/Steam',home/'.steam/steam'):
        for name in (preferred,) if preferred else names:
            p=root/'steamapps/common'/name/'proton'
            if p.is_file():return p
    raise ValueError('Falta Proton 11.0: instalarlo desde Steam, Biblioteca, Herramientas.')

def proton_env(store=None,preferred=None):
    if preferred and preferred not in ('Proton 11.0','Proton - Experimental','Proton 10.0','Proton 9.0 (Beta)','Proton 8.0'):raise ValueError('Versión de Proton no admitida.')
    store=store or Store();slug='project2099' if not preferred or preferred=='Proton 11.0' else 'project2099-'+preferred.lower().replace(' ','-')
    pfx=store.root/'runtimes'/slug;pfx.mkdir(parents=True,exist_ok=True)
    env=clean_environment();env['STEAM_COMPAT_DATA_PATH']=str(pfx)
    env['STEAM_COMPAT_CLIENT_INSTALL_PATH']=str(pathlib.Path.home()/'.local/share/Steam')
    env['WINEDEBUG']='-all';return env

def installer_environment(store):
    """The installer uses current CLR support, independently of the game's Proton."""
    proton=None
    for name in ('Proton 11.0','Proton - Experimental','Proton 10.0'):
        try:proton=proton_path(preferred=name);break
        except ValueError:pass
    if proton is None:raise ValueError('El instalador necesita Proton 11.0, 10.0 o Experimental. Instalalo desde Steam → Biblioteca → Herramientas; el Proton elegido para jugar se conserva.')
    env=proton_env(store)
    prefix=store.root/'runtimes/project2099-installer'
    prefix.mkdir(parents=True,exist_ok=True);env['STEAM_COMPAT_DATA_PATH']=str(prefix)
    return proton,env

def installation_files(folder):
    folder=pathlib.Path(folder)
    if all((folder/n).is_file() for n in ('Project 2099.exe','Engine/Project2099.exe','Engine/rexruntime.dll')):
        return folder/'Project 2099.exe','reeot'
    if all((folder/n).is_file() for n in ('SpiderManEOT.exe','rexruntime.dll')):
        return folder/'SpiderManEOT.exe','legacy'
    return None,''

def entry_for(folder,build=None):
    folder=pathlib.Path(folder);exe,engine=installation_files(folder);exe=exe or folder/'SpiderManEOT.exe'
    if build is None:
        try:build=json.loads((folder/'deck-library-project2099.json').read_text())['version']
        except (OSError,ValueError,KeyError):pass
    if build is None:
        try:
            receipt=json.loads((folder/'Support/Install/INSTALL_RECEIPT.json').read_text())
            build=VERSION if 'BETA 4.1' in receipt.get('PortBuild','') else 'unknown'
        except (OSError,ValueError):build='unknown'
    # Keep the launch target stable across the engine migration, including existing Steam shortcuts.
    return Entry('Spider-Man: Edge of Time',[sys.executable,'-m','deck_library.project2099','run',str(folder/'SpiderManEOT.exe')],'port','Windows',str(exe),str(pathlib.Path(__file__).resolve().parent.parent),game_id='415608B2',metadata={'adapter':'project2099','engine':engine,'build':build,'manual_command':True})

def discover(home,preferences):
    roots=[pathlib.Path(home)/'ports',*map(pathlib.Path,preferences.get('port_roots',[]))];result=[]
    for root in dict.fromkeys(roots):
        if root.is_dir():
            for folder in root.iterdir():
                if not folder.name.startswith('.') and folder.is_dir() and installation_files(folder)[0] and ((folder/'spider_man_edge_of_time.toml').is_file() or (folder/'deck-library-project2099.json').is_file()):
                    result.append(entry_for(folder))
    return result

def prepare(source,destination,store=None,progress=print,cancel=None):
    from . import project2099_update,ports
    store=store or Store();source=pathlib.Path(source).resolve();destination=pathlib.Path(destination).expanduser()
    if destination.is_symlink():raise ValueError('La carpeta de destino es un enlace simbólico.')
    destination=destination.resolve()
    if source.is_dir():
        if not all((source/n).is_file() for n in ('Default.xex','Data/Main.pkz','Data/BaseGameplay.pkz')):raise ValueError('Faltan los datos originales de Xbox 360.')
    else:validate_source(source)
    if destination==destination.parent or (destination.exists() and any(destination.iterdir())):raise ValueError('La carpeta de destino debe estar vacía.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    entry=entry_for(destination, 'unknown');entry.metadata['original_source']=str(source)
    project2099_update.update(entry,source,ports.release_for('GenryTheFox0/Project-2099'),store,progress,cancel,fresh=True)
    progress('Instalación completa');return entry

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['run']);parser.add_argument('executable');parser.add_argument('--proton',choices=['Proton 11.0','Proton - Experimental','Proton 10.0','Proton 9.0 (Beta)','Proton 8.0']);parser.add_argument('--single-queue',action='store_true')
    args=parser.parse_args()
    exe=pathlib.Path(args.executable).resolve()
    actual,engine=installation_files(exe.parent)
    if actual:exe=actual
    if not exe.is_file():raise ValueError('No se encuentra el juego instalado.')
    # Beta 5's .NET launcher needs newer Mono too; legacy gameplay keeps its tested runtime.
    preferred=None if engine=='reeot' else args.proton
    env=proton_env(preferred=preferred)
    if args.single_queue:
        options=[v for v in env.get('VKD3D_CONFIG','').replace(';',',').split(',') if v]
        env['VKD3D_CONFIG']=','.join(dict.fromkeys(options+['single_queue']))
    return subprocess.call([str(proton_path(preferred=preferred)),'run',str(exe)],cwd=exe.parent,env=env)

if __name__=='__main__':sys.exit(main())
