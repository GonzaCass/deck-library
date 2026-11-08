"""Free-space check before unpacking downloaded packages."""
import pathlib,shutil

MARGIN=512*1024*1024

def ensure_space(total,destination):
    """Refuse before writing when the unpacked size would not fit, so a package that expands far beyond its download cannot fill the disk."""
    folder=pathlib.Path(destination)
    while not folder.exists() and folder!=folder.parent:folder=folder.parent
    free=shutil.disk_usage(folder).free
    if total+MARGIN>free:
        raise ValueError(f'El paquete ocupa {total/2**30:.1f} GB al extraerlo y hay {free/2**30:.1f} GB libres. Liberar espacio y volver a intentar.')
