"""Highest settings that suit the Steam Deck screen (1280x800, up to 90 Hz): applied emulator-wide, with a backup of each file.

Only graphics keys are touched; controls, paths, accounts and per-game files stay as they are. An emulator that is
running is skipped, since it would overwrite the file on exit.
"""
import pathlib,re,shutil,time
from .presets import patch_ini

NAMES={'duckstation':'duckstation','dolphin':'dolphin-emu','azahar':'azahar','eden':'eden'}

def running(adapter):
    """True when a process whose name contains the emulator's name is alive."""
    for comm in pathlib.Path('/proc').glob('[0-9]*/comm'):
        try:
            if NAMES[adapter] in comm.read_text().strip().lower():return True
        except OSError:pass
    return False

def qt(**values):
    """Qt-style INI: every value also needs its `\\default=false` marker or the emulator ignores it."""
    out={}
    for key,value in values.items():out[key]=value;out[key+'\\default']=False
    return out

def qt_game(**values):
    """Per-game Qt INI (Eden `custom/<title id>.ini`): a value only counts when both `\\default` and `\\use_global` are false."""
    out={}
    for key,value in values.items():out[key]=value;out[key+'\\default']=False;out[key+'\\use_global']=False
    return out

BOTW='01007EF00011E000'
SWAP_KEY,LAYOUT_KEY='F9','F10'

def shortcut(name,key):
    base='Shortcuts\\Main%20Window\\'+name.replace(' ','%20')+'\\KeySeq'
    return {base:key,base+'\\default':False}

def targets(home):
    flatpak=home/'.var/app/org.DolphinEmu.dolphin-emu/config/dolphin-emu'
    return [
     ('duckstation','DuckStation',home/'.local/share/duckstation/settings.ini',{'GPU':{'ResolutionScale':5,'PGXPEnable':True,'PGXPTextureCorrection':True,'PGXPCulling':True,'DisableInterlacing':True,'Multisamples':1},'Display':{'VSync':True}},True),
     ('dolphin','Dolphin',flatpak/'GFX.ini',{'Settings':{'InternalResolution':3,'ShaderCompilationMode':2,'WaitForShadersBeforeStarting':True},'Enhancements':{'MaxAnisotropy':4}},True),
     ('azahar','Azahar',home/'.config/azahar-emu/qt-config.ini',{'Renderer':qt(resolution_factor=3,async_shader_compilation=True,use_disk_shader_cache=True,use_vsync_new=True,use_hw_shader=True),'Layout':qt(layout_option=1),'UI':{**shortcut('Swap Screens',SWAP_KEY),**shortcut('Toggle Screen Layout',LAYOUT_KEY)}},False),
     ('eden','Eden',home/'.config/eden/qt-config.ini',{'Renderer':qt(use_asynchronous_shaders=True,max_anisotropy=4,use_vsync=1)},False),
     ('eden','Eden (Breath of the Wild)',home/'.config/eden/custom'/(BOTW+'.ini'),{'System':qt_game(language_index=14,region_index=1),'Renderer':qt_game(resolution_setup=2,scaling_filter=5,fsr_sharpening_slider=40,anti_aliasing=0,gpu_accuracy=0)},False),
    ]

def drop_keys(text,section,keys):
    """Remove `keys` (and their `\\default` markers) from one INI section; everything else stays."""
    out=[];current=None;names=set(keys)|{k+'\\default' for k in keys}
    for line in text.splitlines():
        header=re.fullmatch(r'\s*\[([^]]+)\]\s*',line)
        if header:current=header[1]
        elif current==section and line.split('=',1)[0].strip() in names:continue
        out.append(line)
    return '\n'.join(out)+'\n'

MISPLACED={'azahar':('Renderer',('layout_option',))}

def apply(home=None,busy=running):
    """Returns [(emulator, state)] with state applied / present / busy / missing."""
    home=home or pathlib.Path.home();results=[]
    for adapter,name,path,updates,spaced in targets(home):
        if not path.is_file():results.append((name,'missing'));continue
        if busy(adapter):results.append((name,'busy'));continue
        old=path.read_text(encoding='utf-8');base=drop_keys(old,*MISPLACED[adapter]) if adapter in MISPLACED else old;new=patch_ini(base,updates,spaced)
        if new==old:results.append((name,'present'));continue
        shutil.copy2(path,path.with_name(path.name+'.deck-library-'+time.strftime('%Y%m%d-%H%M%S')+'.bak'))
        path.write_text(new,encoding='utf-8');results.append((name,'applied'))
    results.append(('Azahar (idioma de la consola)',set_3ds_language(home,busy=busy)))
    return results

LANGUAGE_BLOCK=0xA0002

def set_3ds_language(home=None,language=5,busy=None):
    """Console language of Azahar's emulated 3DS (0 JP, 1 EN, 2 FR, 3 DE, 4 IT, 5 ES), stored in the config savegame.

    The block table sits at offset 4 with 12-byte entries (id, value or offset, size, flags); a one-byte block keeps its
    value inline. Returns applied / present / busy / missing / unknown.
    """
    import struct
    home=home or pathlib.Path.home();busy=busy or running
    path=home/'Emulation/storage/azahar/nand/data/00000000000000000000000000000000/sysdata/00010017/00000000/config'
    if not path.is_file():return 'missing'
    if busy('azahar'):return 'busy'
    data=bytearray(path.read_bytes())
    if len(data)<8:return 'unknown'
    count=struct.unpack_from('<H',data,0)[0]
    for index in range(min(count,256)):
        offset=4+index*12
        if offset+12>len(data):break
        block,value,size,_=struct.unpack_from('<IIHH',data,offset)
        if block==LANGUAGE_BLOCK and size==1:
            if value==language:return 'present'
            shutil.copy2(path,path.with_name(path.name+'.deck-library-'+time.strftime('%Y%m%d-%H%M%S')+'.bak'))
            struct.pack_into('<I',data,offset+4,language);path.write_bytes(bytes(data));return 'applied'
    return 'unknown'
