"""Transactional ISO import and explicit removal of a verified, redundant source ISO."""
import hashlib,json,pathlib,shutil,tempfile,time
from .models import atomic_json
from .xdvdfs import Image,fingerprint

MANIFEST='.deck-library-iso-import.json'

def prepare(folder,source,spec,progress=print,cancel=None):
    from .original_data import validate
    from .ports import check_cancel
    folder=pathlib.Path(folder).resolve();source=pathlib.Path(source).resolve();target=(folder/spec['destination']).resolve()
    if not target.is_relative_to(folder) or target==folder or source.is_relative_to(target):raise ValueError('El destino de extracción no es válido.')
    if (folder/spec['destination']).is_symlink():raise ValueError('La carpeta de datos es un enlace; no se modificó.')
    with Image(source,cancel) as image:
        image.verify_game(spec)
        existing=details(folder)
        if existing and existing['source']==str(source) and existing['manifest'].get('destination')==spec['destination']:
            try:verify_outputs(folder,spec,existing['manifest'],progress,cancel)
            except (OSError,ValueError):pass
            else:image.unchanged();return str(source)
        if shutil.disk_usage(folder).free<image.total+64*1024**2:raise ValueError('No hay espacio suficiente para extraer y verificar la ISO. El original se conserva.')
        with tempfile.TemporaryDirectory(prefix='.deck-library-import-',dir=folder) as temporary:
            work=pathlib.Path(temporary);staged=work/'game'
            manifest=image.extract(staged,progress)
            validate(staged,spec);image.unchanged();check_cancel(cancel)
            receipt={'schema':1,'source':str(source),'identity':image.identity,'destination':spec['destination'],'title_id':spec['title_id'],'files':manifest,'skipped':image.skipped,'date':time.strftime('%Y-%m-%dT%H:%M:%S'),'removed':False}
            atomic_json(work/'manifest.json',receipt)
            previous=folder/MANIFEST;old_manifest=previous.read_bytes() if previous.is_file() and not previous.is_symlink() else None
            if previous.is_symlink():raise ValueError('El registro de extracción es un enlace; no se modificó.')
            backup=None
            if target.exists():
                backup=folder/'.deck-library-original-backups'/str(time.time_ns())
                if backup.parent.is_symlink():raise ValueError('La carpeta de respaldo es un enlace; no se modificó.')
                backup.parent.mkdir(exist_ok=True);target.rename(backup)
            promoted=False
            try:
                staged.rename(target);promoted=True;(work/'manifest.json').replace(previous)
            except BaseException:
                if promoted:target.rename(staged)
                if backup:backup.rename(target)
                if old_manifest is not None:previous.write_bytes(old_manifest)
                raise
    return str(source)

def details(folder):
    folder=pathlib.Path(folder);path=folder/MANIFEST
    if path.is_symlink():return None
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):return None
    if not isinstance(data,dict) or data.get('schema')!=1 or data.get('removed'):return None
    identity=data.get('identity')
    if not isinstance(data.get('source'),str) or not isinstance(identity,dict) or any(type(identity.get(k)) is not int for k in ('dev','ino','size','mtime_ns','ctime_ns')):return None
    source=pathlib.Path(data['source'])
    if not source.is_absolute() or source.suffix.lower() not in ('.iso','.xiso') or source.is_symlink():return None
    try:
        if fingerprint(source.stat())!=data.get('identity'):return None
    except OSError:return None
    return {'source':str(source),'size':data['identity']['size'],'manifest':data}

def verify_outputs(folder,spec,data,progress=lambda event:None,cancel=None):
    from .original_data import validate
    from .ports import check_cancel
    folder=pathlib.Path(folder).resolve();source=pathlib.Path(data['source'])
    if data['destination']!=spec.get('destination') or data['title_id']!=spec.get('title_id'):raise ValueError('La ISO ya no coincide con el original preparado.')
    root=(folder/data['destination']).resolve()
    if root==folder or not root.is_relative_to(folder) or source.is_relative_to(root):raise ValueError('La ruta de limpieza no es válida.')
    validate(root,spec)
    files=data.get('files')
    if not isinstance(files,list) or not files or len(files)>200000:raise ValueError('El registro de extracción no es válido.')
    with Image(source,cancel) as image:
        image.verify_game(spec)
        expected={(member.path,member.size) for member in image.files}
        if len(files)!=len(expected) or {(row['path'],row['size']) for row in files}!=expected:raise ValueError('El registro de extracción no es válido.')
    total=sum(row['size'] for row in files);done=0
    for row in files:
        check_cancel(cancel);relative=pathlib.PurePosixPath(row['path']);path=root/relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root) or path.is_symlink() or path.stat().st_size!=row['size']:raise ValueError('Los datos extraídos cambiaron o faltan. La ISO se conserva.')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            while block:=stream.read(1024*1024):
                check_cancel(cancel);digest.update(block);done+=len(block);progress({'phase':'verify','done':done,'total':total})
        if digest.hexdigest()!=row['sha256']:raise ValueError('Los datos extraídos cambiaron o faltan. La ISO se conserva.')
    check_cancel(cancel)
    if source.is_symlink() or fingerprint(source.stat())!=data['identity']:raise ValueError('La ISO cambió desde la extracción. No se borró.')

def remove_source(folder,record,progress=lambda event:None,cancel=None):
    from .ports import check_cancel
    folder=pathlib.Path(folder).resolve();info=details(folder)
    if not info or not record.get('configured'):raise ValueError('No hay una ISO verificada pendiente de limpieza.')
    data=info['manifest'];source=pathlib.Path(info['source']);selected=(record.get('inputs') or {}).get('original_data','')
    if not selected or pathlib.Path(selected).resolve()!=source:raise ValueError('La ISO ya no coincide con el original preparado.')
    verify_outputs(folder,record.get('original_data') or {},data,progress,cancel);check_cancel(cancel)
    source.unlink();data['removed']=True
    # Once unlink succeeded, failure to update this optional receipt cannot mean
    # deletion failed. details() also checks source existence before offering it.
    try:atomic_json(folder/MANIFEST,data)
    except OSError:pass
    return info['size']
