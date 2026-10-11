"""UPS patch application (the format fan translations use), with every checksum verified."""
import zlib

def _varint(data,pos):
    value=0;shift=1
    while True:
        byte=data[pos];pos+=1;value+=(byte&0x7f)*shift
        if byte&0x80:return value,pos
        shift<<=7;value+=shift

def apply_ups(source,patch):
    """Return the patched bytes. Raises ValueError when the patch or the source ROM does not match."""
    if patch[:4]!=b'UPS1' or len(patch)<18:raise ValueError('El archivo no es un parche UPS.')
    end=len(patch)-12
    source_crc,target_crc,patch_crc=(int.from_bytes(patch[end+i*4:end+i*4+4],'little') for i in range(3))
    if zlib.crc32(patch[:-4])!=patch_crc:raise ValueError('El parche está dañado.')
    if zlib.crc32(source)!=source_crc:raise ValueError('La ROM original no es la que espera el parche.')
    pos=4;_,pos=_varint(patch,pos);target_size,pos=_varint(patch,pos)
    out=bytearray(source[:target_size].ljust(target_size,b'\0'));cursor=0
    try:
        while pos<end:
            skip,pos=_varint(patch,pos);cursor+=skip
            while patch[pos]:
                out[cursor]^=patch[pos];cursor+=1;pos+=1
            pos+=1;cursor+=1
    except IndexError:raise ValueError('El parche termina de forma inesperada.') from None
    if zlib.crc32(out)!=target_crc:raise ValueError('El resultado no coincide con la suma del parche.')
    return bytes(out)
