"""Keycloak device login. Passwords and provider tokens never enter the desktop app."""
import json,secrets,time,urllib.request,urllib.parse,urllib.error

def request(url,data=None,token=None):
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    if data is not None:headers['Content-Type']='application/x-www-form-urlencoded'
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    req=urllib.request.Request(url,data=urllib.parse.urlencode(data).encode() if data is not None else None,headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=15) as response:raw=response.read(1024*1024+1)
    except urllib.error.HTTPError as error:
        if error.code not in (400,401):raise ValueError('El acceso de cuentas no está disponible.') from None
        raw=error.read(8192)
    if len(raw)>1024*1024:raise ValueError('Respuesta de acceso demasiado grande.')
    return json.loads(raw)

class DeviceAuth:
    def __init__(self,issuer,client):
        self.issuer=issuer.rstrip('/');self.client=client;self.cached=None;self.until=0
        url=urllib.parse.urlsplit(self.issuer)
        if url.scheme!='https' or not url.netloc or url.username or url.password or url.query or url.fragment:raise ValueError('OIDC_ISSUER debe usar HTTPS.')
    def endpoints(self):
        if self.cached and time.time()<self.until:return self.cached
        value=request(self.issuer+'/.well-known/openid-configuration')
        if value.get('issuer')!=self.issuer:raise ValueError('El emisor de cuentas no coincide.')
        for name in ('device_authorization_endpoint','token_endpoint','userinfo_endpoint'):
            url=urllib.parse.urlsplit(value.get(name,''));base=urllib.parse.urlsplit(self.issuer)
            if url.scheme!='https' or url.netloc!=base.netloc or url.username or url.password:raise ValueError('Endpoint de cuentas no permitido.')
        self.cached=value;self.until=time.time()+600;return value
    def start(self):
        value=request(self.endpoints()['device_authorization_endpoint'],{'client_id':self.client,'scope':'openid profile email'})
        if not value.get('device_code'):raise ValueError('No se pudo iniciar sesión. Revisá el cliente deck-library en Keycloak.')
        for key in ('verification_uri','verification_uri_complete'):
            if key in value:
                url=urllib.parse.urlsplit(value[key]);base=urllib.parse.urlsplit(self.issuer)
                if url.scheme!='https' or url.netloc!=base.netloc:raise ValueError('Dirección de acceso no permitida.')
        return value
    def poll(self,code):return request(self.endpoints()['token_endpoint'],{'client_id':self.client,'device_code':code,'grant_type':'urn:ietf:params:oauth:grant-type:device_code'})
    def user(self,token):
        value=request(self.endpoints()['userinfo_endpoint'],token=token)
        if not isinstance(value.get('sub'),str) or not value['sub'] or len(value['sub'])>200:raise ValueError('La cuenta no tiene identidad válida.')
        login=value.get('preferred_username') or value.get('name') or 'Usuario'
        if not isinstance(login,str) or not 1<=len(login)<=100:raise ValueError('Nombre de cuenta inválido.')
        return value['sub'],login
