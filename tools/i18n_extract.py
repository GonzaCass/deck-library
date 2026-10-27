#!/usr/bin/env python3
"""List the Spanish interface strings in the code and presets; with --missing, only those without an English translation."""
import ast,json,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
SPANISH=re.compile(r"[áéíóúñ¿¡Á-Ú]|\b(el|la|los|las|de|del|para|con|sin|una|un|que|se|no|en|por|es|su|al|y|o|desde|este|esta|más|ya|hay|solo|puede|tiene)\b",re.I)
UI_CALLS={'badge','label','button','set_text','set_label','message','confirm','set_status','toast','set_tooltip_text','set_placeholder_text','append','append_text','add_button','InlineDialog','ActionButton','Banner','set_title','pick_file','run_queue','Poster'}

def pieces(node):
    """Static text of a string expression: constants, the literal parts of f-strings (holes become {}) and concatenations."""
    if isinstance(node,ast.Constant) and isinstance(node.value,str):yield node.value
    elif isinstance(node,ast.JoinedStr):yield ''.join(v.value if isinstance(v,ast.Constant) else '{}' for v in node.values)
    elif isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
        yield from pieces(node.left);yield from pieces(node.right)

def collect(root=ROOT):
    found={}
    def add(text,where):
        if isinstance(text,str) and text.strip() and len(text)<=700:found.setdefault(text,[]).append(where)
    for path in sorted(pathlib.Path(root,'deck_library').glob('*.py'))+[pathlib.Path(root,'app.py')]:
        if path.name.startswith('i18n'):continue
        tree=ast.parse(path.read_text());docstrings=set()
        for node in ast.walk(tree):
            if isinstance(node,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and node.body and isinstance(node.body[0],ast.Expr) and isinstance(getattr(node.body[0],'value',None),ast.Constant):docstrings.add(id(node.body[0].value))
        for node in ast.walk(tree):
            where=f'{path.name}:{getattr(node,"lineno",0)}'
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and id(node) not in docstrings:
                if SPANISH.search(node.value) and not re.fullmatch(r'[\w./:%-]+',node.value) and not node.value.startswith(('http','/','~')):add(node.value,where)
            elif isinstance(node,ast.JoinedStr):
                text=''.join(v.value if isinstance(v,ast.Constant) else '{}' for v in node.values)
                if SPANISH.search(text) and not re.fullmatch(r'[\w./:%{}-]+',text):add(text,where)
            if isinstance(node,ast.Call):
                function=node.func;name=function.attr if isinstance(function,ast.Attribute) else getattr(function,'id','')
                if name in UI_CALLS:
                    for argument in node.args[:2]+[k.value for k in node.keywords if k.arg in ('title','label','text')]:
                        for text in pieces(argument):
                            if text.strip() and not re.fullmatch(r'[a-z_]+',text) and len(text)<200:add(text,where)
    def walk(value,where):
        if isinstance(value,dict):
            for key,item in value.items():walk(item,where);walk_key(key,where)
        elif isinstance(value,list):
            for item in value:walk(item,where)
        elif isinstance(value,str) and SPANISH.search(value) and len(value)>3 and not value.startswith(('http','/','~')):add(value,where)
    def walk_key(key,where):
        if SPANISH.search(key) and not re.fullmatch(r'[\w./:%-]+',key):add(key,where)
    for path in [*sorted(pathlib.Path(root,'presets').glob('*.json')),pathlib.Path(root,'catalog/validated-games.json'),pathlib.Path(root,'catalog/port-variants.json')]:walk(json.loads(path.read_text()),path.name)
    return found

def missing(root=ROOT):
    sys.path.insert(0,str(root))
    from deck_library.i18n_en import EXACT
    return {k:v for k,v in collect(root).items() if k not in EXACT}

if __name__=='__main__':
    result=missing() if '--missing' in sys.argv else collect()
    if '--json' in sys.argv:print(json.dumps({k:v[0] for k,v in result.items()},ensure_ascii=False,indent=0))
    else:
        for text,where in result.items():print(where[0],'|',text.replace('\n','\\n'))
        print(len(result),'cadenas',file=sys.stderr)
