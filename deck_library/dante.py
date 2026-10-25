"""Reviewed Dante's Inferno preparation. Originals are staged and identified before promotion."""
import pathlib,re,shutil,struct,subprocess,tempfile,time

TITLE_ID=0x454108CF

def executable(folder):
    return next((p for p in pathlib.Path(folder).iterdir() if p.name.casefold()=='default.xex' and p.is_file()),None)

def title_id(path):
    # XEX2 optional header 0x40006: execution info; title_id is at +0xC.
    with pathlib.Path(path).open('rb') as source:
        header=source.read(24)
        if len(header)!=24 or header[:4]!=b'XEX2':return None
        count=struct.unpack_from('>I',header,20)[0]
        if count>4096:return None
        entries=source.read(count*8)
        if len(entries)!=count*8:return None
        for key,offset in struct.iter_unpack('>II',entries):
            if key==0x40006 and 24+count*8<=offset<=1024*1024:
                source.seek(offset+12);value=source.read(4)
                return int.from_bytes(value,'big') if len(value)==4 else None
    return None

def validate(path):
    if not path:raise ValueError('Elegir la ISO de Xbox 360 o la carpeta extraída de Dante’s Inferno.')
    path=pathlib.Path(path)
    if path.is_dir():
        xex=executable(path)
        if xex and not xex.is_symlink() and title_id(xex)==TITLE_ID:return path
        raise ValueError('La carpeta no contiene un default.xex de Dante’s Inferno de Xbox 360 (454108CF).')
    if path.is_file() and path.suffix.lower() in ('.iso','.xiso'):
        # The disc container is checked here; the actual game identity is checked after extraction.
        with path.open('rb') as stream:
            stream.seek(0x8000)
            if b'PS3VOLUME' in stream.read(100):raise ValueError('Esta ISO es de PS3. Dante’s Inferno requiere la versión de Xbox 360.')
            from .project2099 import check_image
            check_image(stream)
        return path
    raise ValueError('Elegir una ISO/XISO de Xbox 360 o una carpeta extraída con default.xex.')

def find_source(record,games=(),home=None):
    from .ports import ports_root
    home=pathlib.Path(home or pathlib.Path.home());selected=(record.get('inputs') or {}).get('original_data')
    if selected:
        try:return str(validate(selected))
        except (OSError,ValueError):pass
    # An updated installation already has its originals. Never guess an ISO's game from its name.
    existing=ports_root(home)/record.get('folder','')/'game'
    try:return str(validate(existing))
    except (OSError,ValueError):pass
    candidates=[]
    for _,source in games:
        if source:
            path=pathlib.Path(source);candidates.append(path.parent if path.name.lower()=='default.xex' else path)
    roots=[home/'Emulation/roms/xbox360']
    try:
        from .installations import emudeck_paths
        roots.append(pathlib.Path(emudeck_paths(home)['roms'])/'xbox360')
    except (OSError,KeyError):pass
    for root in dict.fromkeys(roots):
        if root.is_dir():candidates.extend(p for p in root.iterdir() if p.is_dir())
    matches=set()
    for candidate in candidates:
        try:
            if candidate.is_dir():matches.add(str(validate(candidate).resolve()))
        except (OSError,ValueError):pass
    return matches.pop() if len(matches)==1 else ''

def arguments(folder=None):
    # The upstream launcher's flat config may contain True/False (not strict TOML).
    settings={}
    if folder is not None:
        try:
            for line in (pathlib.Path(folder)/'dantes_inferno.toml').read_text(encoding='utf-8-sig').splitlines():
                match=re.fullmatch(r'\s*([a-z_]+)\s*=\s*(.*?)\s*',line)
                if match:settings[match[1]]=match[2].strip('"')
        except OSError:pass
    renderer='xenos' if settings.get('renderer_override')=='xenos' else 'dante'
    args=['--game_data_root=game','--renderer='+renderer,'--vsync=true']
    for key,flag,default in [('fullscreen','fullscreen','true'),('smaa','dante_smaa','true'),('show_fps_overlay','show_fps_overlay','false')]:
        value=settings.get(key,default).lower()
        if value in ('true','false'):args.append('--'+flag+'='+value)
    args.append('--input_backend='+('xinput' if settings.get('input_backend')=='xinput' else 'sdl'))
    args.append('--glyph_family='+settings.get('glyph_family','auto') if settings.get('glyph_family','auto') in ('auto','xbox','playstation') else '--glyph_family=auto')
    for key,flag,allowed,default in [('frame_rate','video_mode_refresh_rate',(60,120,180,240),60),('shadow_scale','dante_shadow_scale',(1,2,4),2),('anisotropic_override','anisotropic_override',tuple(range(17)),None),('user_language','user_language',tuple(range(19)),None)]:
        value=settings.get(key,str(default) if default is not None else '')
        if value.isdigit() and int(value) in allowed:args.append('--'+flag+'='+value)
    resolution=settings.get('render_resolution','')
    if re.fullmatch(r'\d{3,5}x\d{3,5}',resolution) and all(320<=int(n)<=16384 for n in resolution.split('x')):args.append('--dante_resolution='+resolution)
    aspect={'4:3':4/3,'16:9':16/9,'21:9':64/27,'32:9':32/9}.get(settings.get('aspect'))
    if aspect:args.append('--ultrawide_target_aspect='+format(aspect,'.4f'))
    if renderer=='xenos':args.extend(['--render_target_path_d3d12=rov','--native_render_scale=auto'])
    return args

def run_extractor(command,*,cwd,env,progress,log,cancel=None):
    # extract-xiso can be silent for a long file. Poll cancellation independently of stdout.
    from .ports import check_cancel
    from .buildenv import stop
    log=pathlib.Path(log)
    with log.open('wb') as output,log.open('r',errors='replace') as reader:
        process=subprocess.Popen(command,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while process.poll() is None:
                check_cancel(cancel)
                try:process.wait(timeout=.2)
                except subprocess.TimeoutExpired:pass
                for line in reader.read(8192).splitlines():
                    if line.strip():progress(line[:160])
            check_cancel(cancel)
            if process.returncode:raise RuntimeError(log.read_text(errors='replace')[-1800:] or 'El proceso terminó con error '+str(process.returncode))
        finally:
            if process.poll() is None:stop(process)

def prepare(folder,path,spec,store,progress,run,cancel=None):
    from .ports import check_cancel
    from . import original_data,port_runtime
    folder=pathlib.Path(folder).resolve();source=validate(path).resolve();target=folder/'game'
    check_cancel(cancel)
    if source==target.resolve():return
    if source.is_dir() and (source==folder or folder.is_relative_to(source)):raise ValueError('Elegir una carpeta original fuera de la instalación del port.')
    with tempfile.TemporaryDirectory(prefix='.dante-data-',dir=folder) as temporary:
        work=pathlib.Path(temporary);staged=work/'game'
        if source.is_file():
            tool=folder/'extract-xiso.exe'
            if not tool.is_file():raise ValueError('Falta extract-xiso.exe en el paquete de Dante’s Inferno. Reinstalar el port o elegir una carpeta extraída.')
            command,env=port_runtime.command_for(folder,store)
            wine=lambda p:'Z:'+str(p).replace('/','\\')
            progress('Extrayendo la ISO de Dante’s Inferno…')
            command=[*command[:2],str(tool),'-x','-d',wine(staged),'-s',wine(source)]
            if run is None:run_extractor(command,cwd=str(folder),env=env,progress=progress,log=work/'extract.log',cancel=cancel)
            else:run(command,cwd=str(folder),env=env,progress=progress,sandbox=False,**({'until':cancel.is_set} if cancel is not None else {}))
            check_cancel(cancel);validate(staged)
        else:original_data.prepare(work,source,spec,progress,cancel=cancel)
        # A mismatching title, failed copy or cancelled extraction never replaces existing data.
        validate(staged)
        for file in staged.rglob('*'):
            check_cancel(cancel)
            if file.is_symlink():raise ValueError('Los datos extraídos contienen enlaces no admitidos.')
        xex=executable(staged)
        if xex.name!='default.xex':xex.rename(staged/'default.xex')
        patch=target/'default.xexp'
        if patch.is_file() and not patch.is_symlink():shutil.copy2(patch,staged/'default.xexp')
        check_cancel(cancel)
        backup=None
        if target.exists():
            if target.is_symlink():raise ValueError('La carpeta game es un enlace; no se modificó.')
            backup=folder/'.deck-library-original-backups'/str(time.time_ns());backup.parent.mkdir(exist_ok=True);target.rename(backup)
        try:staged.rename(target)
        except BaseException:
            if backup:backup.rename(target)
            raise
