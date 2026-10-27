"""Opt-in diagnostics: bounded known logs, redacted preview, ZIP and GitHub draft."""
import datetime,json,os,pathlib,platform,re,urllib.parse,zipfile,tempfile
from . import __version__
from .models import Store
ISSUES='https://github.com/GonzaCass/deck-library/issues/new'
MAX_LOG=16000

def redact(value):
    value=str(value)
    value=re.sub(r'(https?://)[^/\s:@]+:[^/\s@]+@',r'\1<redacted>@',value)
    value=re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)[^\s\"\x27,]+',r'\1<redacted>',value)
    value=re.sub(r'(?i)((?:[\"\x27])?\b(?:password|passwd|token|access_token|refresh_token|client_secret|secret|api_key|apikey|device_code|wait_key|session_code|user_code|code_verifier|id_token|steamgriddb_key)\b(?:[\"\x27])?\s*[:=]\s*)(?:[\"\x27][^\"\x27\n]*[\"\x27]|[^\s,}\n]+)',r'\1"<redacted>"',value)
    value=re.sub(r'(?i)([?&](?:key|token|code|password|secret|session|session_code|user_code|wait_key|device_code|code_verifier|id_token|client_secret)=)[^&\s\"<>]+',r'\1<redacted>',value)
    value=re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]+)\b','<redacted>',value)
    value=re.sub(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b','<redacted>',value)
    value=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '<email>',value)
    value=re.sub(r'/home/[^/\s\"\x27\\]+','~',value)
    value=re.sub(r'(?i)([A-Z]:[\\/](?:users|home)[\\/])[^\\/\s\"\x27]+',r'\1<user>',value)
    value=re.sub(r'(/userdata/)\d+',r'\1<account>',value)
    value=re.sub(r'\b7656119\d{10}\b','<steam-id>',value)
    return value

def tail(path,limit=MAX_LOG):
    with path.open('rb') as stream:
        stream.seek(0,2);stream.seek(max(0,stream.tell()-limit));return stream.read(limit).decode('utf-8','replace')

def collect(store=None,entry=None,include_logs=True):
    store=store or Store();files=[]
    candidates=[('steam-worker.log',store.root/'worker.log')]
    if entry:
        candidates.append(('game-launch.log',store.root/'logs'/(entry.id+'.log')))
        folder=pathlib.Path(entry.source).parent/'logs'
        if folder.is_dir() and not folder.is_symlink():
            game_logs=sorted((p for p in folder.glob('*.log') if not p.is_symlink()),key=lambda p:p.stat().st_mtime,reverse=True)
            candidates.extend(('port-log-'+str(i+1)+'.log',path) for i,path in enumerate(game_logs[:2]))
    candidates.append(('app-error.log',store.root/'logs/app-error.log'))
    for name,path in candidates if include_logs else []:
        try:
            if path.is_file() and not path.is_symlink():files.append({'name':name,'text':redact(tail(path))})
        except OSError:pass
    return {'schema_version':1,'version':__version__,'title':'','description':'','system':{'system':platform.system(),'kernel':platform.release(),'architecture':platform.machine(),'mode':'gaming' if os.environ.get('SteamAppId') or os.environ.get('SteamGameId') else 'desktop'},'game':entry.name if entry else '', 'files':files}

def validate_report(value):
    if not isinstance(value,dict) or set(value)-{'schema_version','version','title','description','system','game','files'} or (type(value.get('schema_version')) is not int or value.get('schema_version')!=1):raise ValueError('Formato de reporte inválido.')
    if len(json.dumps(value,ensure_ascii=False).encode())>110000:raise ValueError('El reporte supera el tamaño permitido.')
    for key,limit in (('version',40),('title',180),('description',8000),('game',200)):
        if not isinstance(value.get(key),str) or len(value[key])>limit:raise ValueError('Campo de reporte inválido: '+key)
    if not value['title'].strip() or not value['description'].strip():raise ValueError('Describir el problema y cómo reproducirlo antes de enviar.')
    system=value.get('system');files=value.get('files')
    if not isinstance(system,dict) or set(system)-{'system','kernel','architecture','mode'} or any(not isinstance(v,str) or len(v)>200 for v in system.values()):raise ValueError('Información de sistema inválida.')
    if not isinstance(files,list) or len(files)>5:raise ValueError('Lista de registros inválida.')
    for item in files:
        if not isinstance(item,dict) or set(item)!={'name','text'} or not isinstance(item['name'],str) or not re.fullmatch(r'[a-z0-9-]+\.log',item['name']) or not isinstance(item['text'],str) or len(item['text'].encode())>MAX_LOG*3:raise ValueError('Registro inválido.')
    return value

def summary(report,reference=''):
    system=report['system'];parts=['Deck Library '+report['version'],report['description'],'Game: '+report.get('game',''),'Mode: '+system.get('mode',''),'System: '+system.get('system','')+' '+system.get('kernel','')+' '+system.get('architecture','')]
    if reference:parts.append('Diagnostic report ID: '+reference)
    parts.append('Steps to reproduce / expected and actual result: see description above.')
    return redact('\n\n'.join(parts))

def issue_url(report,reference=''):
    return ISSUES+'?'+urllib.parse.urlencode({'title':redact(report['title'])[:180],'body':summary(report,reference)[:5000]})

def sanitize(value):
    if isinstance(value,str):return redact(value)
    if isinstance(value,list):return [sanitize(item) for item in value]
    if isinstance(value,dict):return {key:sanitize(item) for key,item in value.items()}
    return value

def export(report,path):
    report=sanitize(report);validate_report(report);path=pathlib.Path(path)
    fd,temporary=tempfile.mkstemp(prefix='.deck-library-report-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as output:
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('report.json',json.dumps(report,ensure_ascii=False,indent=2))
                archive.writestr('summary.txt',summary(report))
                for item in report['files']:archive.writestr(item['name'],item['text'])
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    return path
