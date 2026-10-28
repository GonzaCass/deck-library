"""When each game was last opened, kept apart from settings so a stale settings write can never erase it."""
import time
from .models import atomic_json

LIMIT=300

def load(store):
    try:
        import json
        data=json.loads((store.root/'played.json').read_text())
    except (OSError,ValueError):return {}
    if not isinstance(data,dict):return {}
    return {key:int(value) for key,value in data.items() if isinstance(key,str) and isinstance(value,(int,float))}

def record(store,entry_id,now=None):
    """Remember that `entry_id` was opened now. Never raises: history is a convenience, not part of launching."""
    try:
        played=load(store);played[entry_id]=int(now if now is not None else time.time())
        if len(played)>LIMIT:played=dict(sorted(played.items(),key=lambda item:-item[1])[:LIMIT])
        store.root.mkdir(parents=True,exist_ok=True);atomic_json(store.root/'played.json',played)
    except OSError:pass

def recent(entries,store,limit=6):
    """Entries ordered from the most recently opened, only those that were ever opened."""
    played=load(store);known=[e for e in entries if e.id in played]
    return sorted(known,key=lambda e:-played[e.id])[:limit]
