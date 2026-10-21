"""English interface catalog: Spanish source string -> English. A value equal to its key means "keep as is"; {} marks a value computed at run time."""
import json,pathlib

EXACT={}
for _path in sorted((pathlib.Path(__file__).parent/'i18n_en').glob('*.json')):
    EXACT.update(json.loads(_path.read_text()))
PATTERNS=[]
