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

def targets(home):
    flatpak=home/'.var/app/org.DolphinEmu.dolphin-emu/config/dolphin-emu'
    return [
     ('duckstation','DuckStation',home/'.local/share/duckstation/settings.ini',{'GPU':{'ResolutionScale':5,'PGXPEnable':True,'PGXPTextureCorrection':True,'PGXPCulling':True,'DisableInterlacing':True,'Multisamples':1},'Display':{'VSync':True}},True),
     ('dolphin','Dolphin',flatpak/'GFX.ini',{'Settings':{'InternalResolution':3,'ShaderCompilationMode':2,'WaitForShadersBeforeStarting':True},'Enhancements':{'MaxAnisotropy':4}},True),
     ('azahar','Azahar',home/'.config/azahar-emu/qt-config.ini',{'Renderer':qt(resolution_factor=4,async_shader_compilation=True,use_disk_shader_cache=True,use_vsync_new=True,use_hw_shader=True)},False),
     ('eden','Eden',home/'.config/eden/qt-config.ini',{'Renderer':qt(use_asynchronous_shaders=True,max_anisotropy=4,use_vsync=1)},False),
    ]

def apply(home=None,busy=running):
    """Returns [(emulator, state)] with state applied / present / busy / missing."""
    home=home or pathlib.Path.home();results=[]
    for adapter,name,path,updates,spaced in targets(home):
        if not path.is_file():results.append((name,'missing'));continue
        if busy(adapter):results.append((name,'busy'));continue
        old=path.read_text(encoding='utf-8');new=patch_ini(old,updates,spaced)
        if new==old:results.append((name,'present'));continue
        shutil.copy2(path,path.with_name(path.name+'.deck-library-'+time.strftime('%Y%m%d-%H%M%S')+'.bak'))
        path.write_text(new,encoding='utf-8');results.append((name,'applied'))
    return results
