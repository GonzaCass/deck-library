"""Stable self-shortcut definition, independent of each user's installation path."""
import hashlib,pathlib,sys
from .models import Entry
APP_ID=hashlib.sha256(b'deck-library-app').hexdigest()[:20]

def entry(app=None):
    app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py')
    return Entry('Deck Library',[sys.executable,str(app),'--gaming'],kind='custom',platform='Linux',source=str(app),id=APP_ID,icon=str(app.parent/'assets/icon.png'),metadata={'library_app':True})
