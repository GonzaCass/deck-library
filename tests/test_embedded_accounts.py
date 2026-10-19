"""Authorization boundaries and session lifecycle, without provider credentials."""
import io,json,pathlib,tempfile,time,unittest,urllib.error
from unittest.mock import Mock,patch
from deck_library.auth_policy import origin,account_uri,allowed_navigation
from deck_library import auth_runtime
from deck_library.community import Client
from deck_library.models import Store
from community.server import API,digest

class EmbeddedAccountTests(unittest.TestCase):
    def test_navigation_keeps_forms_on_authorization_origin(self):
        expected=origin('https://auth.example.org/realms/main/device?user_code=123')
        for uri in ('https://auth.example.org/login-actions/registration','about:blank'):
            self.assertTrue(allowed_navigation(uri,expected))
        for uri in ('http://auth.example.org','https://other.example.org','https://user:pass@auth.example.org','javascript:alert(1)','file:///tmp/page'):
            self.assertFalse(allowed_navigation(uri,expected))
        uri=account_uri('https://auth.example.org/device?user_code=ABCD&kc_locale=en')
        self.assertIn('user_code=ABCD',uri);self.assertIn('kc_locale=es',uri);self.assertNotIn('kc_locale=en',uri)
    def test_runtime_prefers_host_or_reuses_installed_runtime(self):
        run=Mock(return_value=Mock(returncode=0))
        self.assertEqual(auth_runtime.command('/app/auth_browser.py',123,run)[-2:],['/app/auth_browser.py','123'])
        run=Mock(side_effect=[Mock(returncode=1),Mock(returncode=0)])
        with patch('deck_library.auth_runtime.shutil.which',return_value='/usr/bin/flatpak'):
            args=auth_runtime.command('/app/auth_browser.py',123,run)
        self.assertIn('org.gnome.Platform//50',args);self.assertIn('--filesystem=/app:ro',args);self.assertNotIn('--filesystem=home',args)
    def test_missing_runtime_does_not_install_silently(self):
        with patch('deck_library.auth_runtime.shutil.which',return_value=None),self.assertRaises(auth_runtime.MissingRuntime):
            auth_runtime.command('/app/auth_browser.py',123,Mock(return_value=Mock(returncode=1)))
    def test_cancelled_poll_does_not_save_a_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=Client(Store(tmp),'https://presets.example.org');value={'state':'connected','token':'opaque-test','login':'Player'}
            with patch.object(client,'request',return_value=value):self.assertEqual(client.poll('wait',persist=False),value)
            self.assertFalse(client.path.exists());client.remember(value);self.assertEqual(client.path.stat().st_mode&0o777,0o600)
    def test_identity_endpoint_requires_current_unexpired_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=API(pathlib.Path(tmp)/'db')
            with self.assertRaises(PermissionError):api.handle('GET','/v1/me',{}, {})
            with api.db() as db:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('test'),'id','Player',time.time()+60))
            self.assertEqual(api.handle('GET','/v1/me',{}, {},'test'),{'login':'Player'})
            api.handle('POST','/v1/logout',{}, {},'test')
            with self.assertRaises(PermissionError):api.handle('GET','/v1/me',{}, {},'test')
    def test_expired_client_session_is_cleared_on_401(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=Client(Store(tmp),'https://presets.example.org');client.remember({'token':'expired','login':'Player'})
            error=urllib.error.HTTPError(client.url+'/v1/me',401,'Unauthorized',{},io.BytesIO(b'{"error":"Session expired"}'))
            with patch('urllib.request.build_opener') as opener:
                opener.return_value.open.side_effect=error
                with self.assertRaises(ValueError):client.me()
            self.assertFalse(client.path.exists())
