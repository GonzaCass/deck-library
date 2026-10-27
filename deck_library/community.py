"""HTTPS community client. Public ratings queries use only game and adapter IDs."""
import json,os,pathlib,urllib.parse,urllib.request,urllib.error
from . import presets
from .models import atomic_json

class Client:
    def __init__(self,store,url):
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Ingresar una dirección HTTPS del servicio.')
        self.store=store;self.url=url.rstrip('/');self.path=store.root/'community-session.json'
    def session(self):
        try:
            value=json.loads(self.path.read_text());return value if value.get('server')==self.url else {}
        except (OSError,ValueError):return {}
    def request(self,path,body=None,token=None):
        headers={'User-Agent':'DeckLibrary-Community','Accept':'application/json'};token=self.session().get('token') if token is None else token
        if token:headers['Authorization']='Bearer '+token
        if body is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request(self.url+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers=headers)
        # Do not forward a bearer token to an HTTP redirect or another host.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        try:
            with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:raw=response.read(2*1024*1024+1)
        except urllib.error.HTTPError as error:
            try:message=json.loads(error.read(8192)).get('error','Solicitud rechazada.')
            except (ValueError,AttributeError):message='Solicitud rechazada por el servicio.'
            if error.code==401 and token==self.session().get('token'):self.path.unlink(missing_ok=True)
            raise ValueError(message) from None
        if len(raw)>2*1024*1024:raise ValueError('Respuesta demasiado grande.')
        return json.loads(raw)
    def providers(self):return self.request('/v1/auth/providers').get('providers',[])
    def start(self,provider='keycloak'):
        value=self.request('/v1/auth/start',{'provider':provider})
        for key in ('verification_uri','verification_uri_complete'):
            if key not in value:continue
            url=urllib.parse.urlsplit(value[key])
            if url.scheme!='https' or not url.netloc or url.username or url.password:raise ValueError('Dirección de autorización no permitida.')
        return value
    def poll(self,key,persist=True):
        value=self.request('/v1/auth/poll',{'wait_key':key})
        if value.get('state')=='connected' and persist:self.remember(value)
        return value
    def remember(self,value):
        atomic_json(self.path,{'server':self.url,'token':value['token'],'login':value['login']});self.path.chmod(0o600)
    def me(self):return self.request('/v1/me')
    def logout(self):
        try:self.request('/v1/logout',{})
        finally:self.path.unlink(missing_ok=True)
    def search(self,entry,mine=False):
        query=urllib.parse.urlencode({'game':presets.public_game_id(entry).lower(),'adapter':presets.adapter_for(entry)})
        if not presets.public_game_id(entry):raise ValueError('Completar el ID del juego antes de buscar perfiles.')
        rows=self.request(('/v1/me/presets?' if mine else '/v1/presets?')+query).get('presets',[])
        for row in rows:
            if not presets.compatible(entry,row['preset']):raise ValueError('El servicio devolvió un perfil de otro juego.')
        return rows
    def download(self,row):
        value=presets.validate(row['preset']);value={**value,'id':'community-'+row['id']}
        records=self.metadata();records[value['id']]={k:row[k] for k in ('id','rating','ratings','author') if k in row};atomic_json(self.store.root/'community-profiles.json',records)
        return self._save(value)
    def metadata(self):
        try:return json.loads((self.store.root/'community-profiles.json').read_text())
        except (OSError,ValueError):return {}
    def _save(self,value):
        presets.validate(value);atomic_json(self.store.root/'presets'/(value['id']+'.json'),value);return value
    def publish(self,value):return self.request('/v1/presets',presets.validate(value))
    def feedback(self,row,result,notes=''):return self.request('/v1/presets/'+row['id']+'/feedback',{'result':result,'notes':notes})
    def comments(self,row):return self.request('/v1/presets/'+row['id']+'/feedback').get('comments',[])
    def rate(self,row,rating,notes):return self.request('/v1/presets/'+row['id']+'/feedback',{'rating':rating,'notes':notes})
