"""Navigation rules for the isolated account view."""
import urllib.parse

def origin(uri):
    parsed=urllib.parse.urlsplit(uri)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('La página de acceso debe usar HTTPS.')
    return parsed.scheme+'://'+parsed.netloc

def account_uri(uri,language='es'):
    origin(uri)
    parsed=urllib.parse.urlsplit(uri);query=urllib.parse.parse_qsl(parsed.query,keep_blank_values=True)
    query=[(k,v) for k,v in query if k!='kc_locale'];query.append(('kc_locale','en' if language=='en' else 'es'))
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))

def allowed_navigation(uri,expected):
    if uri=='about:blank':return True
    try:return origin(uri)==expected
    except (ValueError,TypeError):return False
