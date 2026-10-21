"""Interface language. The code and the catalog keys are Spanish; English is applied where text reaches a widget."""
import functools,json,locale,os,re,sys

LANGUAGES=('es','en')
_language='es'
_missed=set()

def detect(preferences=None):
    """Language to use: DECK_LIBRARY_LANG, then the saved choice, then the system locale (Spanish installs keep Spanish)."""
    forced=os.environ.get('DECK_LIBRARY_LANG','').strip().lower()
    if forced in LANGUAGES:return forced
    preferences=preferences or {}
    choice=preferences.get('language')
    if choice in LANGUAGES:return choice
    if choice is None and preferences.get('onboarding_complete'):return 'es'  # an existing installation keeps the language it has always had
    names=[os.environ.get(k,'') for k in ('LC_ALL','LC_MESSAGES','LANGUAGE','LANG')]
    try:names.append((locale.getlocale()[0] or ''))
    except (ValueError,TypeError):pass
    for name in names:
        if name.lower().startswith('es'):return 'es'
        if name.lower().startswith('en'):return 'en'
    return 'en'

def language():return _language

def set_language(value):
    global _language
    _language=value if value in LANGUAGES else 'es';translate.cache_clear()

def _catalog():
    from .i18n_en import EXACT,PATTERNS
    return EXACT,PATTERNS

@functools.lru_cache(maxsize=8192)
def _patterns():
    exact,_=_catalog()
    compiled=[]
    for key,value in exact.items():
        if '{}' not in key or value==key or len(key.replace('{}','').strip())<4:continue
        parts=key.split('{}');regex='^'+'(.+?)'.join(re.escape(p) for p in parts)+'$'
        compiled.append((len(key),re.compile(regex,re.S),value))
    compiled.sort(key=lambda item:-item[0])
    return tuple((rx,value) for _,rx,value in compiled)

@functools.lru_cache(maxsize=1)
def _pieces():
    exact,_=_catalog()
    def fragment(k):return k!=k.strip() or k.rstrip()[-1:] in ':…·' or k[:1].islower()
    keys=sorted((k for k in exact if '{}' not in k and len(k.strip())>=6 and re.search(r'[A-Za-zÁ-úñ]{4}',k) and exact[k]!=k and fragment(k)),key=len,reverse=True)
    return tuple((k,exact[k]) for k in keys)

@functools.lru_cache(maxsize=1)
def _inline():
    """Placeholder keys matched inside a longer text (e.g. a status line with a suffix); the hole stands for one token."""
    exact,_=_catalog();rules=[]
    for key,value in exact.items():
        if '{}' not in key or value==key or len(key.replace('{}','').strip())<6:continue
        rules.append((len(key),re.compile('(?<!\\w)'+r'(\S+)'.join(re.escape(p) for p in key.split('{}'))),value))
    rules.sort(key=lambda item:-item[0])
    return tuple((rx,value) for _,rx,value in rules)

def _fill(template,groups):
    index=iter(groups)
    return re.sub(r'\{\}',lambda _:next(index,''),template)

def _core(text):
    """Exact or whole-text pattern match, or None."""
    exact,_=_catalog()
    if text in exact:return exact[text]
    stripped=text.strip()
    if stripped!=text and stripped in exact:return text.replace(stripped,exact[stripped])
    for rx,value in _patterns():
        match=rx.match(text)
        if match:return _fill(value,[translate(g) for g in match.groups()])
    return None

@functools.lru_cache(maxsize=16384)
def translate(text):
    """English text for a Spanish interface string; anything unknown (game names, paths, data) is returned unchanged."""
    if _language=='es' or not isinstance(text,str) or not text.strip():return text
    found=_core(text)
    if found is not None:return found
    if '\n' in text:
        lines=text.split('\n');done=[translate(line) if line.strip() else line for line in lines]
        if done!=lines:return '\n'.join(done)
    if re.search(r'\s{2,}·\s{2,}',text):
        parts=re.split(r'(\s{2,}·\s{2,})',text);done=[];index=0;changed=False
        while index<len(parts):
            part=parts[index];separator=bool(re.fullmatch(r'\s{2,}·\s{2,}',part))
            if separator and index+1<len(parts):
                value=_core(part+parts[index+1])
                if value is not None:done.append(value);index+=2;changed=True;continue
            if not separator:
                value=translate(part)
                if value!=part:changed=True
                done.append(value);index+=1;continue
            done.append(part);index+=1
        if changed:return ''.join(done)
    result=text
    for key,value in _pieces():
        if key in result:result=result.replace(key,value)
    for rx,value in _inline():
        result=rx.sub(lambda m,value=value:_fill(value,[translate(g) for g in m.groups()]),result)
    if result==text and os.environ.get('DECK_LIBRARY_I18N_LOG') and re.search(r'[A-Za-zÁ-úñ]{3}',text) and len(text)<300:
        _missed.add(text)
    return result

def missed():return sorted(_missed)

def dump_missed():
    path=os.environ.get('DECK_LIBRARY_I18N_LOG')
    if path and _missed:
        with open(path,'a') as handle:
            for text in sorted(_missed):handle.write(json.dumps(text,ensure_ascii=False)+'\n')
        _missed.clear()

t=translate

def install_gtk_hooks():
    """Translate at the widget boundary so program logic keeps working with the Spanish source strings."""
    from gi.repository import Gtk,Atk
    if getattr(Gtk,'_deck_i18n',False):return
    Gtk._deck_i18n=True
    def wrap_method(cls,name,positions=(0,)):
        original=getattr(cls,name)
        def method(self,*args,**kwargs):
            args=list(args)
            for index in positions:
                if index<len(args) and isinstance(args[index],str):args[index]=translate(args[index])
            return original(self,*args,**kwargs)
        method.__name__=name;setattr(cls,name,method)
    def wrap_init(cls,keys):
        original=cls.__init__
        def init(self,*args,**kwargs):
            for key in keys:
                if isinstance(kwargs.get(key),str):kwargs[key]=translate(kwargs[key])
            original(self,*args,**kwargs)
        cls.__init__=init
    for cls,keys in ((Gtk.Label,('label',)),(Gtk.Button,('label',)),(Gtk.CheckButton,('label',)),(Gtk.ToggleButton,('label',)),(Gtk.LinkButton,('label',)),(Gtk.Expander,('label',)),(Gtk.Frame,('label',)),(Gtk.Window,('title',)),(Gtk.Entry,('placeholder_text',))):
        wrap_init(cls,keys)
    for cls,name in ((Gtk.Label,'set_text'),(Gtk.Label,'set_label'),(Gtk.Label,'set_markup'),(Gtk.Button,'set_label'),(Gtk.Widget,'set_tooltip_text'),(Gtk.Widget,'set_tooltip_markup'),(Gtk.Entry,'set_placeholder_text'),(Gtk.Window,'set_title'),(Gtk.ComboBoxText,'append_text'),(Gtk.ComboBoxText,'prepend_text'),(Gtk.Frame,'set_label'),(Gtk.Expander,'set_label'),(Gtk.MenuItem,'set_label'),(Atk.Object,'set_name'),(Atk.Object,'set_description')):
        wrap_method(cls,name)
    wrap_method(Gtk.ComboBoxText,'append',(1,));wrap_method(Gtk.ComboBoxText,'insert',(2,));wrap_method(Gtk.Dialog,'add_button',(0,))
    def wrap_factory(cls,name,positions):
        original=getattr(cls,name)
        def factory(*args,**kwargs):
            args=list(args)
            for index in positions:
                if index<len(args) and isinstance(args[index],str):args[index]=translate(args[index])
            return original(*args,**kwargs)
        setattr(cls,name,factory)
    for cls,name,positions in ((Gtk.Label,'new',(0,)),(Gtk.Button,'new_with_label',(0,)),(Gtk.CheckButton,'new_with_label',(0,)),(Gtk.ToggleButton,'new_with_label',(0,)),(Gtk.LinkButton,'new_with_label',(1,)),(Gtk.Expander,'new',(0,)),(Gtk.Frame,'new',(0,))):
        try:wrap_factory(cls,name,positions)
        except AttributeError:pass

def setup(preferences=None):
    set_language(detect(preferences))
    if _language!='es':install_gtk_hooks()
    return _language
