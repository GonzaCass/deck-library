"""Synthetic PE headers with import descriptors; contain no executable game code."""
import struct


def image(imports=(),architecture='x64'):
    data=bytearray(4096);data[:2]=b'MZ';struct.pack_into('<I',data,60,128)
    data[128:132]=b'PE\0\0';optional=240 if architecture=='x64' else 224
    struct.pack_into('<HH',data,132,0x8664 if architecture=='x64' else 0x14c,1);struct.pack_into('<H',data,148,optional)
    header=152;struct.pack_into('<H',data,header,0x20b if architecture=='x64' else 0x10b)
    directories=112 if architecture=='x64' else 96;struct.pack_into('<I',data,header+directories-4,16)
    if imports:struct.pack_into('<II',data,header+directories+8,0x1000,20*(len(imports)+1))
    section=header+optional;struct.pack_into('<IIII',data,section+8,3584,0x1000,3584,512)
    offset=1024
    for i,name in enumerate(imports):
        struct.pack_into('<I',data,512+i*20+12,0x1000+offset-512)
        encoded=name.encode()+b'\0';data[offset:offset+len(encoded)]=encoded;offset+=len(encoded)
    return bytes(data)
