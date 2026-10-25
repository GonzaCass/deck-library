"""Copy user-selected originals into a reviewed port layout, without altering the source."""
import pathlib,shutil

def validate(path,spec):
    if not path:raise ValueError('Faltan los archivos originales.')
    path=pathlib.Path(path)
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

def prepare(folder,path,spec,progress=print,cancel=None):
    folder=pathlib.Path(folder).resolve();source=validate(path,spec).resolve();target=(folder/spec['destination']).resolve()
    if not target.is_relative_to(folder):raise ValueError('El destino sale de la carpeta del port.')
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
