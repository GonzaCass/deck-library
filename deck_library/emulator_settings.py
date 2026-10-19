"""Small verified language adapter; other emulators keep their own controller editor."""
import pathlib
from . import presets
from .content import eden_paths
LANGUAGES={'1':'Inglés (EE. UU.)','12':'Inglés (Reino Unido)','5':'Español (España)','14':'Español (Latinoamérica)','2':'Francés','3':'Alemán','4':'Italiano','17':'Portugués (Brasil)','0':'Japonés'}
SLUGS={'Switch':'eden','Wii':'dolphin-emu','GameCube':'dolphin-emu','PlayStation':'duckstation','PlayStation 2':'pcsx2-qt','PSP':'ppsspp','Nintendo 3DS':'azahar','Wii U':'cemu'}

def inspect_emulator(entry,preferences=None):
    preferences=preferences or {};slug=SLUGS.get(entry.platform,'');languages={};language=None
    lines=['Emulador: '+(slug or 'Comando personalizado')]
    if slug=='eden':
        paths=eden_paths(config_dir=preferences.get('eden_config') or None);global_path=paths['config']/'qt-config.ini';game=presets.target_for(entry,preferences.get('eden_config') or None)
        local=presets.ini_parser(game.read_text() if game.exists() else '');global_=presets.ini_parser(global_path.read_text() if global_path.exists() else '')
        group=local['System'] if local.has_section('System') else {}
        if 'language_index' in group and group.get('language_index\\use_global')!='true':language=group['language_index']
        elif global_.has_section('System'):language=global_['System'].get('language_index')
        languages=LANGUAGES;lines.extend(['Idioma del juego: '+LANGUAGES.get(language,'Predeterminado / no identificado'),'Configuración global y controles: '+str(global_path),'Configuración del juego: '+str(game)])
        if global_.has_section('UI'):lines.append('Idioma de la interfaz: '+global_['UI'].get('language','predeterminado'))
        lines.append('El idioma del juego y el de la interfaz son opciones distintas. El juego debe incluir ese idioma.')
    else:lines.append('La edición de idioma de este emulador se realiza en su configuración original.')
    return {'summary':'\n'.join(lines),'languages':languages,'language':language,'slug':slug}

def set_language(entry,value,store,preferences=None):
    if SLUGS.get(entry.platform)!='eden' or value not in LANGUAGES:raise ValueError('Idioma no compatible con este adaptador.')
    profile=presets.manual_profile(entry,{'System':{'language_index':int(value)}})
    return presets.apply(entry,profile,store,(preferences or {}).get('eden_config') or None)
