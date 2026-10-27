"""Copy user-selected originals into a reviewed port layout, without altering the source."""
import pathlib,shutil

def validate(path,spec):
    if not path:raise ValueError('Faltan los archivos originales.')
    path=pathlib.Path(path)
    if spec.get('kind')=='xbox360':
        from .dante import executable,title_id
        from .ports import sha256_file
        if path.is_dir() and not spec.get('iso_only'):
            xex=executable(path)
            if xex and not xex.is_symlink() and title_id(xex)==int(spec['title_id'],16):
                if spec.get('sha256') and sha256_file(xex) not in spec['sha256']:raise ValueError('default.xex no coincide con la revisión admitida por el port.')
                return path
        if path.is_file() and spec.get('iso') and path.suffix.lower() in (('.iso',) if spec.get('iso_only') else ('.iso','.xiso')):
            if spec.get('extract_iso'):
                from .xdvdfs import Image
                with Image(path) as image:image.verify_game(spec)
                return path
            from .project2099 import check_image
            with path.open('rb') as stream:check_image(stream)
            return path
        raise ValueError('Elegir la ISO de Xbox 360.' if spec.get('iso_only') else 'Elegir una carpeta extraída de Xbox 360 con default.xex del juego y la revisión admitida.')
    if spec.get('kind')=='xbox360-dante':
        from .dante import validate as check
        return check(path)
    if spec.get('kind')=='switch-dump':
        if path.is_dir() and (path/'exefs/main').is_file() and (path/'romfs').is_dir():return path
        raise ValueError('Elegir la carpeta extraída con exefs/main y romfs de Bayonetta 2 v1.2. No sirve un NSP/XCI cifrado.')
    if path.is_file() and spec.get('iso') and path.suffix.lower() in ('.iso','.xiso') and path.stat().st_size:return path
    if path.is_dir() and (path/'default.xbe').is_file():
        from .ports import sha256_file
        if spec.get('sha256') and sha256_file(path/'default.xbe') not in spec['sha256']:raise ValueError('default.xbe no coincide con las versiones de BLACK admitidas por este port.')
        return path
    raise ValueError('Elegir una carpeta extraída que contenga default.xbe'+(' o una imagen ISO/XISO de Xbox.' if spec.get('iso') else '.'))

def find_source(record,games=(),home=None):
    """Find reviewed extracted originals by identity, never by a similar game name."""
    from .ports import ports_root
    spec=record['original_data'];selected=(record.get('inputs') or {}).get('original_data')
    # An explicit invalid choice stays visible as an error; do not silently replace it.
    if selected and pathlib.Path(selected).exists():return str(validate(selected,spec))
    home=pathlib.Path(home or pathlib.Path.home());existing=ports_root(home)/record.get('folder','')/spec['destination']
    if spec.get('iso_only') and record.get('configured_with'):
        name=record.get('configured_with','')
        if name and pathlib.Path(name).name==name:
            try:return str(validate(existing/name,spec))
            except (OSError,ValueError):pass
    try:return str(validate(existing,spec))
    except (OSError,ValueError):pass
    # An ISO's container is not proof of its title/revision. Only auto-detect folders.
    if spec.get('kind')!='xbox360' or spec.get('iso_only'):return ''
    candidates=[]
    for game in games:
        if not isinstance(game,(tuple,list)) or len(game)!=2 or not game[1]:continue
        path=pathlib.Path(game[1]);candidates.append(path.parent if path.name.lower()=='default.xex' else path)
    roots=[home/'Emulation/roms/xbox360']
    try:
        from .installations import emudeck_paths
        roots.append(pathlib.Path(emudeck_paths(home)['roms'])/'xbox360')
    except (OSError,KeyError):pass
    for root in dict.fromkeys(roots):
        if root.is_dir():candidates.extend(p for p in root.iterdir() if p.is_dir())
    found=set()
    for candidate in candidates:
        if not candidate.is_dir():continue
        try:found.add(str(validate(candidate,spec).resolve()))
        except (OSError,ValueError):pass
    return found.pop() if len(found)==1 else ''

def prepare(folder,path,spec,progress=print,cancel=None):
    if spec.get('extract_iso') and pathlib.Path(path).is_file():
        from .iso_import import prepare as extract
        return extract(folder,path,spec,progress,cancel)
    folder=pathlib.Path(folder).resolve();source=validate(path,spec).resolve();target=(folder/spec['destination']).resolve()
    if not target.is_relative_to(folder):raise ValueError('El destino sale de la carpeta del port.')
    if source==target:return str(source)
    if source==folder or folder.is_relative_to(source):raise ValueError('Elegir los archivos originales fuera de la instalación del port.')
    files=[source] if source.is_file() else [p for p in source.rglob('*') if p.is_file() or p.is_symlink()]
    planned=[]
    from .ports import sha256_file,check_cancel
    for file in files:
        check_cancel(cancel)
        if file.is_symlink():raise ValueError('La carpeta original contiene enlaces. Elegir una copia extraída con archivos normales.')
        destination=target/(file.name if source.is_file() else file.relative_to(source))
        if not destination.resolve().is_relative_to(folder):raise ValueError('Un destino sale de la carpeta del port.')
        if destination.exists():
            if not destination.is_file() or sha256_file(destination)!=sha256_file(file):raise ValueError('El destino contiene otro archivo: '+destination.name+'. No se sobrescribió.')
        else:planned.append((file,destination))
    for i,(file,destination) in enumerate(planned):
        check_cancel(cancel)
        progress(f'Copiando archivos originales: {i+1}/{len(planned)}');destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,destination)
    return str(source)
