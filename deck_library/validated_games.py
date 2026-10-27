"""Curated gameplay reports; installation scores and community votes never certify a game."""
import json,pathlib,re
from . import presets

def catalog(path=None):
    path=pathlib.Path(path or pathlib.Path(__file__).resolve().parent.parent/'catalog/validated-games.json')
    value=json.loads(path.read_text())
    if value.get('schema_version')!=1 or not isinstance(value.get('games'),list):raise ValueError('Catálogo de juegos validados inválido.')
    found=set()
    for game in value['games']:
        if set(game)!={'id','name','game_id','adapter','program','version','repository','hardware','date','profile_id','result','limitations'}:raise ValueError('Ficha de validación incompleta.')
        if not re.fullmatch(r'[a-z0-9-]{1,80}',game['id']) or game['id'] in found or game['adapter'] not in presets.REGISTRY:raise ValueError('Identidad de validación inválida.')
        if game['hardware'] not in ('steam-deck-lcd','steam-deck-oled') or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',game['date']):raise ValueError('Prueba sin equipo o fecha.')
        if any(not isinstance(v,str) or len(v)>1000 for v in game.values()):raise ValueError('Datos de validación inválidos.')
        if game['repository'] and not re.fullmatch(r'[\w.-]+/[\w.-]+',game['repository']):raise ValueError('Repositorio de validación inválido.')
        found.add(game['id'])
    return value['games']

def matching(game,entries):
    return next((entry for entry in entries if (game['repository'] and entry.metadata.get('port_repository','').casefold()==game['repository'].casefold()) or (presets.public_game_id(entry).casefold()==game['game_id'].casefold() and presets.adapter_for(entry)==game['adapter'])),None)
