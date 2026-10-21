"""Extract 7z/RAR members as regular files, validating names before writing anything."""
import pathlib,re,shutil,subprocess

def extract(archive,destination):
    tool=shutil.which('7z') or shutil.which('7zz')
    if not tool:raise ValueError('Este paquete necesita 7-Zip (7z o 7zz). Instalarlo o elegir el ZIP del proyecto.')
    result=subprocess.run([tool,'l','-slt','-ba','--',str(archive)],capture_output=True,text=True,timeout=60,check=True)
    root=pathlib.Path(destination).resolve();records=[];seen=set()
    for block in result.stdout.strip().split('\n\n'):
        fields=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        if 'Path' not in fields:continue
        name=fields['Path'].replace('\\','/');path=pathlib.PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or re.match(r'^[A-Za-z]:',name):raise ValueError('El paquete contiene rutas inseguras.')
        if name in seen:raise ValueError('El paquete repite un destino.')
        seen.add(name)
        target=root/name
        if not target.resolve().is_relative_to(root):raise ValueError('El paquete contiene rutas inseguras.')
        if fields.get('Encrypted')=='+':raise ValueError('El paquete está cifrado; usar una descarga pública sin contraseña.')
        if fields.get('Symbolic Link') or fields.get('Hard Link') or re.search(r'\bl[rwx-]{9}',fields.get('Attributes','')):raise ValueError('Este paquete contiene enlaces no admitidos por el extractor 7z.')
        records.append((fields['Path'],target,fields.get('Folder')=='+'))
    if not records:raise ValueError('El archivo comprimido está vacío o no se pudo interpretar.')
    for name,target,directory in records:
        if directory:target.mkdir(parents=True,exist_ok=True);continue
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('wb') as out:subprocess.run([tool,'x','-so','--',str(archive),name],stdout=out,stderr=subprocess.PIPE,check=True,timeout=300)
