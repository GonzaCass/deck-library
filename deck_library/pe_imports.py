"""Bounded, read-only PE import inspection. No game code is loaded or executed."""
import pathlib,struct


def inspect(path):
    with pathlib.Path(path).open('rb') as stream:
        size=stream.seek(0,2)
        def read(offset,length):
            if offset<0 or length<0 or offset+length>size:raise ValueError('Ejecutable Windows truncado.')
            stream.seek(offset);data=stream.read(length)
            if len(data)!=length:raise ValueError('Ejecutable Windows truncado.')
            return data
        dos=read(0,64)
        if dos[:2]!=b'MZ':raise ValueError('No es un ejecutable Windows PE.')
        pe=struct.unpack_from('<I',dos,60)[0]
        if pe>16*1024*1024:raise ValueError('Cabecera Windows fuera de rango.')
        header=read(pe,24)
        if header[:4]!=b'PE\0\0':raise ValueError('Cabecera Windows no reconocida.')
        machine,sections=struct.unpack_from('<HH',header,4);optional_size=struct.unpack_from('<H',header,20)[0]
        if machine not in (0x14c,0x8664) or not 0<sections<=96 or optional_size>4096:raise ValueError('Arquitectura Windows no admitida.')
        optional=read(pe+24,optional_size);magic=struct.unpack_from('<H',optional)[0]
        if (machine,magic) not in ((0x14c,0x10b),(0x8664,0x20b)):raise ValueError('Formato Windows no admitido.')
        directories=96 if magic==0x10b else 112
        if len(optional)<directories:raise ValueError('Cabecera Windows incompleta.')
        count=min(struct.unpack_from('<I',optional,directories-4)[0],16)
        imagebase=struct.unpack_from('<I' if magic==0x10b else '<Q',optional,28 if magic==0x10b else 24)[0]
        table=read(pe+24+optional_size,sections*40);ranges=[]
        for i in range(sections):
            virtual_size,rva,raw_size,offset=struct.unpack_from('<IIII',table,i*40+8)
            ranges.append((rva,raw_size,offset))
        def location(rva,length):
            for start,extent,offset in ranges:
                if start<=rva and rva+length<=start+extent:return offset+rva-start
            raise ValueError('Tabla de dependencias Windows fuera de rango.')
        def name(rva):
            out=bytearray()
            for index in range(256):
                c=read(location(rva+index,1),1)
                if c==b'\0':
                    value=out.decode('ascii').lower()
                    if not value or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_.-' for c in value):raise ValueError('Nombre de DLL no válido.')
                    return value
                out.extend(c)
            raise ValueError('Nombre de DLL demasiado largo.')
        imports=set()
        for index,length,field in ((1,20,12),(13,32,4)):
            if index>=count or len(optional)<directories+(index+1)*8:continue
            rva,extent=struct.unpack_from('<II',optional,directories+index*8)
            if not rva:continue
            if extent<length or extent>1024*1024:raise ValueError('Tabla de dependencias Windows no válida.')
            for n in range(min(extent//length,4096)):
                row=read(location(rva+n*length,length),length)
                if not any(row):break
                ref=struct.unpack_from('<I',row,field)[0]
                if index==13 and not struct.unpack_from('<I',row)[0]&1:ref-=imagebase
                imports.add(name(ref))
            else:raise ValueError('Tabla de dependencias Windows sin terminador.')
        return {'architecture':'x64' if machine==0x8664 else 'x86','imports':sorted(imports)}
