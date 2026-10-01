"""Read local Steam Input profiles; never edit configsets or share account fields."""
import pathlib,re,json

def parse_text(text):
    # Preserve repeated group/binding keys as pairs.
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[{}]|//[^\n]*',text);tokens=[t for t in tokens if not t.startswith('//')];index=0
    def atom(token):
        if not token.startswith('"'):raise ValueError('VDF de controles inválido.')
        return re.sub(r'\\(["\\])',r'\1',token[1:-1])
    def object_(nested=False,depth=0):
        nonlocal index
        if depth>32:raise ValueError('VDF demasiado anidado.')
        pairs=[]
        while index<len(tokens):
            token=tokens[index];index+=1
            if token=='}':
                if not nested:raise ValueError('VDF inválido.')
                return pairs
            key=atom(token)
            if index>=len(tokens):raise ValueError('VDF truncado.')
            value=tokens[index];index+=1
            pairs.append((key,object_(True,depth+1) if value=='{' else atom(value)))
        if nested:raise ValueError('VDF truncado.')
        return pairs
    return object_()

def first(pairs,key,default=''):return next((v for k,v in pairs if k==key),default)

def bindings(pairs,prefix=''):
    rows=[]
    for key,value in pairs:
        if key=='binding' and isinstance(value,str):rows.append((prefix,value.split(',')[0]))
        elif isinstance(value,list):
            name=prefix
            if key.startswith(('button_','dpad_','left_','right_')) or key in ('click','pull','edge','touch'):name=(prefix+' / '+key).strip(' / ')
            rows.extend(bindings(value,name))
    return rows

def local_profiles(entry,home=None):
    home=pathlib.Path(home or pathlib.Path.home());account=pathlib.Path(entry.metadata.get('steam_account',''))
    if not account.is_absolute():return []
    steam=account.parent.parent.parent;root=steam/'steamapps/common/Steam Controller Configs'/account.parent.name/'config'
    names={re.sub(r'[<>:"/\\|?*]','',name).casefold() for name in (entry.name,entry.metadata.get('steam_name','')) if name}
    names.add(str(entry.metadata.get('steam_appid','')))
    profiles=[]
    if not root.is_dir():return profiles
    for folder in root.iterdir():
        if not folder.is_dir() or folder.name.casefold() not in names:continue
        for path in folder.glob('*.vdf'):
            try:
                if path.stat().st_size>2*1024*1024:continue
                document=parse_text(path.read_text());mapping=first(document,'controller_mappings',[])
                if not isinstance(mapping,list):continue
                localized=first(mapping,'localization',[]);spanish=first(localized,'spanish',[]) if isinstance(localized,list) else []
                title=first(spanish,'title') if isinstance(spanish,list) else ''
                if not title:title=first(mapping,'title')
                if title.startswith('#'):title='Perfil guardado en Steam'
                modes=[first(v,'mode') for k,v in mapping if k=='group' and isinstance(v,list)]
                profiles.append({'path':str(path),'title':title,'controller':first(mapping,'controller_type'),'bindings':bindings(mapping),'modes':list(dict.fromkeys(m for m in modes if m)),'revision':first(mapping,'revision')})
            except (OSError,ValueError):continue
    return profiles
