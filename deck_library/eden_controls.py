"""Map Eden's player 1 to the Steam Deck's own controls, only on request and with a backup of qt-config.ini."""
import datetime,pathlib,re,shutil
from .content import eden_paths,emulator_busy
from .presets import patch_ini

DECK_GUID='03000000de280000ff11000001000000'  # Steam's virtual gamepad, which is what SDL sees on the Deck
SDL=f'engine:sdl,port:0,guid:{DECK_GUID}'

def deck_values():
    """The Controls section Eden writes after mapping the Deck pad (Nintendo layout: A right, B bottom)."""
    button=lambda n:f'"{SDL},button:{n}"'
    hat=lambda d:f'"{SDL},direction:{d},hat:0"'
    trigger=lambda n:f'"engine:sdl,invert:+,port:0,guid:{DECK_GUID},axis:{n},threshold:0.500000"'
    stick=lambda x,y:f'"{SDL},axis_x:{x},offset_x:-0.000000,axis_y:{y},offset_y:0.000000,invert_x:+,invert_y:+,deadzone:0.150000"'
    values={'a':button(1),'b':button(0),'x':button(3),'y':button(2),'l':button(4),'r':button(5),'sl':button(4),'sr':button(5),'zl':trigger(2),'zr':trigger(5),
            'plus':button(7),'minus':button(6),'home':button(8),'lstick':button(9),'rstick':button(10),
            'ddown':hat('down'),'dleft':hat('left'),'dright':hat('right'),'dup':hat('up')}
    result={f'player_0_button_{k}':v for k,v in values.items()}
    result.update({'player_0_lstick':stick(0,1),'player_0_rstick':stick(3,4),'player_0_connected':'true','player_0_type':0})
    return {key:v for key,v in result.items()},{f'{key}\\default':'false' for key in result}

def config_path(config_dir=None):return eden_paths(config_dir=config_dir or None)['config']/'qt-config.ini'

def status(config_dir=None):
    """'ok' when player 1 already uses the Deck pad, 'missing' when nothing is mapped, 'other' when another device is."""
    path=config_path(config_dir)
    if not path.is_file():return 'missing'
    match=re.search(r'^player_0_button_a=(.*)$',path.read_text(errors='replace'),re.M)
    if not match or '[empty]' in match[1] or not match[1].strip():return 'missing'
    return 'ok' if DECK_GUID in match[1] else 'other'

def apply(config_dir=None):
    """Write the mapping; returns the backup path. The global file is changed only in player 1's keys."""
    if emulator_busy():raise RuntimeError('Eden debe estar cerrado para actualizar el mando.')
    path=config_path(config_dir);old=path.read_text() if path.is_file() else ''
    backup=None
    if old:
        backup=path.with_name(path.name+'.deck-library-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.bak');shutil.copy2(path,backup)
    values,defaults=deck_values()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(patch_ini(old,{'Controls':{**values,**defaults}}))
    return backup
