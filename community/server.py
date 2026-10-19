"""WSGI JSON service. SQLite, validated presets and device authentication."""
import contextlib,hashlib,json,os,pathlib,re,secrets,sqlite3,time,urllib.parse,urllib.request
from deck_library.presets import validate
from .oidc import DeviceAuth
LIMIT=128*1024

def digest(value):return hashlib.sha256(value.encode()).hexdigest()

def github(url,data=None,token=None):
    headers={'Accept':'application/json','User-Agent':'DeckLibrary-Community'}
    if token:headers['Authorization']='Bearer '+token
    request=urllib.request.Request(url,data=urllib.parse.urlencode(data).encode() if data is not None else None,headers=headers)
    with urllib.request.urlopen(request,timeout=15) as response:raw=response.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('Respuesta de GitHub demasiado grande.')
    return json.loads(raw)

class API:
    def __init__(self,path=None,client_id=None,oidc_issuer=None,oidc_client=None):
        self.path=str(path or os.environ.get('COMMUNITY_DB','/data/community.sqlite3'));self.client_id=client_id or os.environ.get('GITHUB_CLIENT_ID','')
        issuer=oidc_issuer or os.environ.get('OIDC_ISSUER','');client=oidc_client or os.environ.get('OIDC_CLIENT_ID','')
        self.oidc=DeviceAuth(issuer,client) if issuer and client else None
        pathlib.Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.executescript('''PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS tokens(hash TEXT PRIMARY KEY, uid TEXT NOT NULL, login TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS devices(hash TEXT PRIMARY KEY, code TEXT NOT NULL, expires REAL NOT NULL, next_poll REAL NOT NULL, interval INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS presets(id TEXT PRIMARY KEY, uid TEXT NOT NULL, login TEXT NOT NULL, game TEXT NOT NULL, adapter TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS feedback(preset TEXT NOT NULL, uid TEXT NOT NULL, result TEXT NOT NULL, notes TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY(preset,uid));
            CREATE TABLE IF NOT EXISTS rates(key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL);''')
            db.execute('BEGIN IMMEDIATE')
            for table,column,definition in [('devices','provider',"TEXT NOT NULL DEFAULT 'github'"),('feedback','rating','INTEGER'),('feedback','author',"TEXT NOT NULL DEFAULT ''")]:
                if column not in {r['name'] for r in db.execute('PRAGMA table_info('+table+')')}:db.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' '+definition)
    @contextlib.contextmanager
    def db(self):
        with contextlib.closing(sqlite3.connect(self.path,timeout=10)) as connection:
            connection.row_factory=sqlite3.Row
            with connection:yield connection
    def session(self,token):
        with self.db() as db:row=db.execute('SELECT uid,login FROM tokens WHERE hash=? AND expires>?',(digest(token),time.time())).fetchone()
        if row is None:raise PermissionError('Iniciá sesión para publicar o comentar.')
        return dict(row)
    def rate(self,key,limit=30,seconds=60):
        now=time.time()
        with self.db() as db:
            db.execute('DELETE FROM rates WHERE expires<?',(now,));db.execute('INSERT INTO rates VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,now+seconds));row=db.execute('SELECT count FROM rates WHERE key=?',(key,)).fetchone()
            if row['count']>limit:raise ValueError('Demasiadas solicitudes. Esperá antes de repetir.')
    def seed_profiles(self,game,adapter,remote='local'):
        from deck_library import presets
        from deck_library.models import Store,Entry
        platforms={'eden':'Switch','wiicompiled':'WiiCompiled','prism':'Minecraft','dolphin':'Wii','duckstation':'PlayStation','project2099':'Windows'}
        if adapter not in platforms or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}',game):return
        with self.db() as db:
            if db.execute("SELECT 1 FROM presets WHERE game=? AND adapter=? AND uid='builtin'",(game.lower(),adapter)).fetchone():return
        self.rate('seed:'+remote,30,3600)
        entry=Entry(game,['unused'],platform=platforms[adapter],game_id=game,metadata={'adapter':adapter})
        if presets.public_game_id(entry).lower()!=game.lower():return
        catalog_store=Store(pathlib.Path(self.path).parent/'catalog')
        values=presets.recommended(entry,catalog_store)
        with self.db() as db:
            for value in values:
                identifier=digest('builtin:'+value['id'])[:32]
                db.execute("INSERT OR IGNORE INTO presets VALUES(?,?,?,?,?,?,?,?)",(identifier,'builtin',value['author'],game.lower(),adapter,json.dumps(value,ensure_ascii=False),'approved',time.time()))
    def handle(self,method,path,query,body,token='',remote='local'):
        now=time.time()
        if method=='GET' and path=='/health':return {'ok':True,'schema_version':1,'login_available':bool(self.client_id or self.oidc)}
        if method=='GET' and path=='/v1/auth/providers':return {'providers':([{'id':'keycloak','name':'Cuenta propia'}] if self.oidc else [])+([{'id':'github','name':'GitHub'}] if self.client_id else [])}
        if path.startswith('/v1/auth/'):
            self.rate('auth:'+remote,40)
            if method=='POST' and path=='/v1/auth/start' and body.get('provider')=='keycloak':
                if not self.oidc:raise ValueError('El acceso con cuenta propia todavía no está configurado.')
                value=self.oidc.start();secret=secrets.token_urlsafe(32);interval=max(5,int(value.get('interval',5)))
                with self.db() as db:db.execute('INSERT INTO devices(hash,code,expires,next_poll,interval,provider) VALUES(?,?,?,?,?,?)',(digest(secret),value['device_code'],now+min(int(value['expires_in']),900),now+interval,interval,'keycloak'))
                return {**{key:value[key] for key in ('user_code','verification_uri','verification_uri_complete') if key in value},'wait_key':secret,'interval':interval}
            if method=='POST' and path=='/v1/auth/poll':
                with self.db() as db:device=db.execute('SELECT * FROM devices WHERE hash=? AND expires>?',(digest(body.get('wait_key','')),now)).fetchone()
                if device and device['provider']=='keycloak':
                    if now<device['next_poll']:return {'state':'pending','interval':device['interval']}
                    with self.db() as db:db.execute('UPDATE devices SET next_poll=? WHERE hash=?',(now+device['interval'],device['hash']))
                    value=self.oidc.poll(device['code'])
                    if value.get('error') in ('authorization_pending','slow_down'):
                        interval=device['interval']+(5 if value['error']=='slow_down' else 0)
                        with self.db() as db:db.execute('UPDATE devices SET interval=?,next_poll=? WHERE hash=?',(interval,now+interval,device['hash']))
                        return {'state':'pending','interval':interval}
                    if not value.get('access_token'):raise ValueError('La autorización se rechazó o venció. Volvé a iniciar sesión.')
                    sub,login=self.oidc.user(value['access_token']);uid='oidc:'+digest(self.oidc.issuer)[:16]+':'+sub;session=secrets.token_urlsafe(40)
                    with self.db() as db:
                        db.execute('DELETE FROM devices WHERE hash=?',(device['hash'],));db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest(session),uid,login,now+30*86400))
                    return {'state':'connected','token':session,'login':login}
            if method=='POST' and path=='/v1/auth/start':
                if not self.client_id:raise ValueError('El servidor todavía no tiene configurado el acceso con GitHub.')
                value=github('https://github.com/login/device/code',{'client_id':self.client_id,'scope':''})
                if not value.get('device_code'):raise ValueError('GitHub no pudo iniciar la autenticación.')
                secret=secrets.token_urlsafe(32);interval=max(5,int(value['interval']))
                with self.db() as db:
                    db.execute('DELETE FROM devices WHERE expires<?',(now,));db.execute('INSERT INTO devices(hash,code,expires,next_poll,interval) VALUES(?,?,?,?,?)',(digest(secret),value['device_code'],now+min(int(value['expires_in']),900),now+interval,interval))
                return {'wait_key':secret,'user_code':value['user_code'],'verification_uri':'https://github.com/login/device','interval':interval}
            if method=='POST' and path=='/v1/auth/poll':
                key=digest(body.get('wait_key',''))
                with self.db() as db:
                    row=db.execute('SELECT * FROM devices WHERE hash=? AND expires>?',(key,now)).fetchone()
                    if row is None:raise ValueError('El código venció. Iniciá sesión otra vez.')
                    if now<row['next_poll']:return {'state':'pending','interval':row['interval']}
                    db.execute('UPDATE devices SET next_poll=? WHERE hash=?',(now+row['interval'],key))
                value=github('https://github.com/login/oauth/access_token',{'client_id':self.client_id,'device_code':row['code'],'grant_type':'urn:ietf:params:oauth:grant-type:device_code'})
                if value.get('error') in ('authorization_pending','slow_down'):
                    interval=row['interval']+(5 if value['error']=='slow_down' else 0)
                    with self.db() as db:db.execute('UPDATE devices SET interval=?,next_poll=? WHERE hash=?',(interval,now+interval,key))
                    return {'state':'pending','interval':interval}
                if not value.get('access_token'):raise ValueError('GitHub rechazó o venció la autorización.')
                user=github('https://api.github.com/user',token=value['access_token']);uid=str(user['id']);login=user['login'];session=secrets.token_urlsafe(40)
                with self.db() as db:
                    db.execute('DELETE FROM tokens WHERE expires<?',(now,));db.execute('DELETE FROM devices WHERE hash=?',(key,));db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest(session),uid,login,now+30*86400))
                return {'state':'connected','token':session,'login':login}
        if method=='POST' and path=='/v1/logout':
            with self.db() as db:db.execute('DELETE FROM tokens WHERE hash=?',(digest(token),))
            return {'ok':True}
        if method=='GET' and path=='/v1/me/presets':
            user=self.session(token);game=query.get('game',[''])[0];adapter=query.get('adapter',[''])[0]
            with self.db() as db:rows=db.execute("SELECT id,login,body,updated,status FROM presets WHERE uid=? AND (?='' OR game=?) AND (?='' OR adapter=?) ORDER BY updated DESC LIMIT 25",(user['uid'],game,game,adapter,adapter)).fetchall()
            return {'presets':[{'id':r['id'],'author':r['login'],'preset':json.loads(r['body']),'updated':r['updated'],'status':r['status']} for r in rows]}
        if method=='GET' and path=='/v1/presets':
            game=query.get('game',[''])[0];adapter=query.get('adapter',[''])[0]
            self.seed_profiles(game,adapter,remote)
            with self.db() as db:rows=db.execute("SELECT id,login,body,updated,(SELECT COUNT(*) FROM feedback f WHERE f.preset=presets.id AND result='works') AS works,(SELECT COUNT(*) FROM feedback f WHERE f.preset=presets.id AND result='issues') AS issues FROM presets WHERE status='approved' AND (?='' OR game=?) AND (?='' OR adapter=?) ORDER BY updated DESC LIMIT 25",(game,game,adapter,adapter)).fetchall()
            values=[]
            with self.db() as db:
                for r in rows:
                    stats=db.execute('SELECT AVG(rating) AS average,COUNT(rating) AS count FROM feedback WHERE preset=?',(r['id'],)).fetchone()
                    values.append({'id':r['id'],'author':r['login'],'preset':json.loads(r['body']),'updated':r['updated'],'works':r['works'],'issues':r['issues'],'rating':stats['average'],'ratings':stats['count']})
            return {'presets':values}
        if method=='POST' and path=='/v1/presets':
            user=self.session(token);self.rate('post:'+user['uid'],10,3600);value=validate(body)
            if value['license']!='MIT':raise ValueError('La publicación comunitaria requiere licencia MIT.')
            value={**value,'author':user['login']};identifier=digest(user['uid']+':'+value['id'])[:32]
            with self.db() as db:
                db.execute("INSERT INTO presets VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body,game=excluded.game,adapter=excluded.adapter,status='pending',updated=excluded.updated",(identifier,user['uid'],user['login'],value['game']['id'].lower(),value['adapter']['id'],json.dumps(value,ensure_ascii=False),'pending',now))
            return {'id':identifier,'status':'pending'}
        match=re.fullmatch(r'/v1/presets/([a-f0-9]{32})/feedback',path)
        if method=='GET' and match:
            with self.db() as db:
                if not db.execute("SELECT 1 FROM presets WHERE id=? AND status='approved'",(match[1],)).fetchone():raise FileNotFoundError('Perfil no disponible.')
                rows=db.execute("SELECT author,rating,result,notes,updated FROM feedback WHERE preset=? ORDER BY updated DESC LIMIT 50",(match[1],)).fetchall()
            return {'comments':[dict(row) for row in rows]}
        if method=='POST' and match:
            user=self.session(token);self.rate('feedback:'+user['uid'],30,3600)
            rating=body.get('rating');result=body.get('result') or ('works' if rating is not None and type(rating) is int and rating>=3 else 'issues');notes=body.get('notes','')
            if rating is not None and (type(rating) is not int or not 1<=rating<=5):raise ValueError('La valoración debe estar entre 1 y 5.')
            if result not in ('works','issues') or not isinstance(notes,str) or len(notes)>2000:raise ValueError('Comentario inválido.')
            with self.db() as db:
                if not db.execute("SELECT 1 FROM presets WHERE id=? AND status='approved'",(match[1],)).fetchone():raise ValueError('Perfil no disponible.')
                db.execute('INSERT INTO feedback(preset,uid,result,notes,updated,rating,author) VALUES(?,?,?,?,?,?,?) ON CONFLICT(preset,uid) DO UPDATE SET result=excluded.result,notes=excluded.notes,updated=excluded.updated,rating=excluded.rating,author=excluded.author',(match[1],user['uid'],result,notes,now,rating,user['login']))
            return {'ok':True}
        raise FileNotFoundError('Ruta no disponible.')
    def __call__(self,environ,start_response):
        try:
            method=environ.get('REQUEST_METHOD','GET');size=int(environ.get('CONTENT_LENGTH') or 0)
            if not 0<=size<=LIMIT:raise ValueError('El documento supera 128 KiB.')
            if method in ('POST','PUT') and not environ.get('CONTENT_TYPE','').startswith('application/json'):raise ValueError('Se requiere JSON.')
            raw=environ['wsgi.input'].read(size) if size else b'{}';body=json.loads(raw)
            if not isinstance(body,dict):raise ValueError('Se requiere un objeto JSON.')
            value=self.handle(method,environ.get('PATH_INFO','/'),urllib.parse.parse_qs(environ.get('QUERY_STRING','')),body,environ.get('HTTP_AUTHORIZATION','').removeprefix('Bearer '),environ.get('REMOTE_ADDR','unknown'));status='200 OK'
        except PermissionError as error:status='401 Unauthorized';value={'error':str(error)}
        except FileNotFoundError as error:status='404 Not Found';value={'error':str(error)}
        except (ValueError,TypeError,KeyError) as error:status='400 Bad Request';value={'error':str(error)}
        except Exception:status='503 Service Unavailable';value={'error':'El servicio no pudo completar la solicitud.'}
        data=json.dumps(value,ensure_ascii=False).encode();start_response(status,[('Content-Type','application/json; charset=utf-8'),('Content-Length',str(len(data))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff')]);return [data]

def application(environ,start_response):
    global _api
    if _api is None:_api=API()
    return _api(environ,start_response)
_api=None

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['pending','approve','reject','backup']);parser.add_argument('id',nargs='?');args=parser.parse_args();api=API()
    with api.db() as db:
        if args.action=='pending':print(json.dumps([dict(r) for r in db.execute("SELECT id,login,body FROM presets WHERE status='pending'")],ensure_ascii=False,indent=2))
        elif args.action=='backup':
            if not args.id:parser.error('Falta el archivo de destino.')
            with contextlib.closing(sqlite3.connect(args.id)) as target:db.backup(target)
        else:
            if not args.id:parser.error('Falta el ID.')
            changed=db.execute('UPDATE presets SET status=? WHERE id=?',('approved' if args.action=='approve' else 'rejected',args.id)).rowcount
            if not changed:raise SystemExit('No se encontró el perfil.')
            print(args.action+': '+args.id)
