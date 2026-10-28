"""Private support requests, account-owned replies and read receipts."""
import re,secrets,time

CATEGORIES=('port','emulated','native','minecraft')
STATES=('new','investigating','fixed','declined')

def fields(body):
    title=' '.join(str(body.get('title','')).split())[:120]
    platform=' '.join(str(body.get('platform','')).split())[:60]
    details=str(body.get('details','')).strip()
    category=str(body.get('category','emulated'))
    repository=str(body.get('repository','')).strip().rstrip('/')
    if len(title)<2:raise ValueError('Indicar el nombre del juego o de la instancia.')
    if not platform:raise ValueError('Indicar la plataforma.')
    if category not in CATEGORIES:raise ValueError('Elegir el tipo de solicitud.')
    if len(details)>2000:raise ValueError('La descripción supera 2000 caracteres.')
    if re.search(r'magnet:|\.(nsp|xci|nsz|xcz|iso|rom|pkg|zip|7z|rar)\b|https?://',title+' '+platform+' '+details,re.I):
        raise ValueError('No se aceptan enlaces ni archivos de juegos. Usar el campo GitHub para el repositorio del port.')
    if category=='port':
        if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*',repository):
            raise ValueError('Indicar el repositorio del port: https://github.com/autor/proyecto.')
    elif repository:raise ValueError('El repositorio de GitHub corresponde solo a solicitudes de ports.')
    return title,platform,details,category,repository

def create(api,body,token,remote):
    api.rate('request:'+remote,5,3600);api.rate('request:all',300,3600)
    title,platform,details,category,repository=fields(body)
    try:user=api.session(token)
    except PermissionError:user={'uid':'','login':''}
    identifier=secrets.token_hex(4);now=time.time()
    with api.db() as db:
        db.execute('INSERT INTO game_requests(id,login,title,platform,details,state,note,created,updated,uid,category,repository) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   (identifier,user['login'],title,platform,details,'new','',now,now,user['uid'],category,repository))
    api.notify(identifier,title,platform)
    return {'id':identifier,'received':True}

def mine(api,token):
    user=api.session(token)
    with api.db() as db:
        rows=db.execute("SELECT id,title,platform,state,note,created,updated,category,repository,seen FROM game_requests WHERE uid=? AND uid!='' ORDER BY updated DESC LIMIT 100",(user['uid'],)).fetchall()
        result=[]
        for row in rows:
            value=dict(row);seen=value.pop('seen')
            messages=[dict(r) for r in db.execute('SELECT note,state,created FROM request_replies WHERE request=? ORDER BY id',(row['id'],))]
            value.update(replies=messages,unread=bool(messages and messages[-1]['created']>seen))
            result.append(value)
    return {'requests':result,'unread':sum(r['unread'] for r in result)}

def read(api,identifier,body,token):
    user=api.session(token)
    observed=body.get('updated')
    if type(observed) not in (float,int) or not 0<=observed<=time.time()+1:raise ValueError('Fecha de lectura no válida.')
    with api.db() as db:
        changed=db.execute("UPDATE game_requests SET seen=MAX(seen,MIN(updated,?)) WHERE id=? AND uid=? AND uid!=''",(observed,identifier,user['uid'])).rowcount
    if not changed:raise FileNotFoundError('No se encontró la solicitud.')
    return {'ok':True}

def reply(api,identifier,body):
    with api.db() as db:
        row=db.execute('SELECT * FROM game_requests WHERE id=?',(identifier,)).fetchone()
        if not row:raise FileNotFoundError('No se encontró la solicitud.')
        state=str(body.get('state',row['state']));note=str(body.get('note','')).strip()
        if state not in STATES:raise ValueError('Estado no válido.')
        if len(note)>2000:raise ValueError('La respuesta supera 2000 caracteres.')
        if state==row['state'] and not note:raise ValueError('Escribir una respuesta o cambiar el estado.')
        now=time.time()
        db.execute('UPDATE game_requests SET state=?,note=?,updated=? WHERE id=?',(state,note or row['note'],now,identifier))
        db.execute('INSERT INTO request_replies(request,note,state,created) VALUES(?,?,?,?)',(identifier,note,state,now))
    return {'ok':True}
