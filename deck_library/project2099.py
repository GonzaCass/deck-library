"""Project-2099 preparation using the pinned official installer, under Proton."""
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

def entry_for(folder,build=None):
    folder=pathlib.Path(folder);exe=folder/'SpiderManEOT.exe'
    if build is None:
        try:build=json.loads((folder/'deck-library-project2099.json').read_text())['version']
        except (OSError,ValueError,KeyError):pass
    if build is None:
        try:
            receipt=json.loads((folder/'Support/Install/INSTALL_RECEIPT.json').read_text())
            build=VERSION if 'BETA 4.1' in receipt.get('PortBuild','') else 'unknown'
        except (OSError,ValueError):build='unknown'
    return Entry('Spider-Man: Edge of Time',[sys.executable,'-m','deck_library.project2099','run',str(exe)],'port','Windows',str(exe),str(pathlib.Path(__file__).resolve().parent.parent),game_id='415608B2',metadata={'adapter':'project2099','build':build,'manual_command':True})

def discover(home,preferences):
    roots=[pathlib.Path(home)/'ports',*map(pathlib.Path,preferences.get('port_roots',[]))];result=[]
    for root in dict.fromkeys(roots):
        if root.is_dir():
            for folder in root.iterdir():
                if folder.is_dir() and all((folder/n).is_file() for n in ('SpiderManEOT.exe','rexruntime.dll')) and ((folder/'spider_man_edge_of_time.toml').is_file() or (folder/'deck-library-project2099.json').is_file()):
                    result.append(entry_for(folder))
    return result

def prepare(source,destination,store=None,progress=print):
    store=store or Store();source=pathlib.Path(source).resolve();destination=pathlib.Path(destination).expanduser().resolve()
    iso_size=validate_source(source) # No downloads or writes for a PS3 source.
    proton=proton_path()
    if destination==destination.parent or destination.is_symlink() or (destination.exists() and any(destination.iterdir())):
        raise ValueError('La carpeta de destino debe estar vacía.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(destination.parent).free<iso_size+18*1024**3:
        raise ValueError('Se necesitan 18 GB libres, más el tamaño de la ISO si está dentro de un ZIP o 7z.')
    cache=store.root/'downloads/project2099';cache.mkdir(parents=True,exist_ok=True)
    for name,digest in ASSETS.items():
        p=cache/name
        if not p.exists() or hashlib.file_digest(p.open('rb'),'sha256').hexdigest()!=digest:
            progress('Descargando '+name)
            temporary=p.with_suffix(p.suffix+'.part')
            urllib.request.urlretrieve('https://github.com/GenryTheFox0/Project-2099/releases/download/v'+VERSION+'/'+name,temporary)
            if hashlib.file_digest(temporary.open('rb'),'sha256').hexdigest()!=digest:raise ValueError('SHA-256 incorrecto: '+name)
            temporary.replace(p)
    with tempfile.TemporaryDirectory(prefix='project2099-',dir=destination.parent) as tmp:
        tmp=pathlib.Path(tmp);image=source
        if iso_size:
            progress('Extrayendo ISO')
            image=tmp/'source.iso'
            if source.suffix.lower()=='.7z':
                tool,name,size=sevenzip_image(source)
                with image.open('wb') as out:
                    result=subprocess.run([tool,'e','-so',str(source),name],stdout=out,stderr=subprocess.PIPE)
                if result.returncode or image.stat().st_size!=size:raise ValueError('Error de integridad al extraer la ISO del 7z.')
            else:
                with zipfile.ZipFile(source) as z, z.open(next(i for i in z.infolist() if i.filename.lower().endswith('.iso'))) as inp,image.open('wb') as out:shutil.copyfileobj(inp,out,1024*1024)
            with image.open('rb') as inp:check_image(inp)
        progress('Verificando componentes')
        with zipfile.ZipFile(cache/('EOT-PC-Payload-v'+VERSION+'.zip')) as z:
            for i in z.infolist():
                if not (tmp/i.filename).resolve().is_relative_to(tmp):raise ValueError('Ruta insegura en payload.')
            z.extractall(tmp)
        win=lambda p:'Z:'+str(p).replace('/','\\')
        command=[str(proton),'run',str(cache/('EOTInstaller-v'+VERSION+'.exe')),'--install-test',win(image),win(destination),win(tmp/'payload'),'5']
        progress('Instalando y verificando archivos del juego')
        log=cache/'install.log'
        with log.open('w') as out:result=subprocess.run(command,env=proton_env(store),stdout=out,stderr=subprocess.STDOUT)
        if result.returncode or not (destination/'SpiderManEOT.exe').is_file():
            raise RuntimeError('El instalador rechazó el origen o no terminó. Registro: '+str(log)+'\n'+log.read_text(errors='replace')[-2500:])
    entry=entry_for(destination,VERSION);entry.metadata['original_source']=str(source)
    from . import presets
    profile=next(p for p in presets.catalog(store) if p['id']=='project2099-deck-720p60')
    presets.apply(entry,profile,store);store.merge([entry]);progress('Instalación completa');return entry

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['run']);parser.add_argument('executable');parser.add_argument('--proton',choices=['Proton 11.0','Proton - Experimental','Proton 10.0','Proton 9.0 (Beta)','Proton 8.0']);parser.add_argument('--single-queue',action='store_true')
    args=parser.parse_args()
    exe=pathlib.Path(args.executable).resolve()
    if not exe.is_file():raise ValueError('No se encuentra el juego instalado.')
    env=proton_env(preferred=args.proton)
    if args.single_queue:
        options=[v for v in env.get('VKD3D_CONFIG','').replace(';',',').split(',') if v]
        env['VKD3D_CONFIG']=','.join(dict.fromkeys(options+['single_queue']))
    return subprocess.call([str(proton_path(preferred=args.proton)),'run',str(exe)],cwd=exe.parent,env=env)

if __name__=='__main__':sys.exit(main())
