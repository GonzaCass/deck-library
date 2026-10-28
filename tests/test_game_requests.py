"""Game requests: anyone can ask, only the configured administrators can read, and no game file or link is ever accepted."""
import json,pathlib,tempfile,time,unittest
from unittest.mock import patch
from community.server import API,digest

class GameRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.api=API(pathlib.Path(self.temp.name)/'community.db',client_id='public-test');self.api.admins={'owner'}
        with self.api.db() as db:
            db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('owner-session'),'oidc:aaaa:sub-owner','Owner',time.time()+100))
            db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('github-session'),'555','Owner',time.time()+100))
            db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('player-session'),'oidc:aaaa:sub-player','Player',time.time()+100))
    def tearDown(self):self.temp.cleanup()
    def ask(self,title='Mi juego',platform='Switch',details='No abre',token='',remote='local'):
        return self.api.handle('POST','/v1/requests',{}, {'title':title,'platform':platform,'details':details},token,remote)
    def test_a_request_is_stored_privately_and_returns_a_reference(self):
        result=self.ask(token='player-session');self.assertTrue(result['received']);self.assertRegex(result['id'],'^[0-9a-f]{8}$')
        with self.api.db() as db:row=dict(db.execute('SELECT * FROM game_requests').fetchone())
        self.assertEqual((row['title'],row['platform'],row['state'],row['login']),('Mi juego','Switch','new','Player'))
    def test_an_anonymous_or_expired_session_still_sends_the_request_without_an_author(self):
        self.ask();self.ask(token='unknown-session')
        with self.api.db() as db:self.assertEqual([r['login'] for r in db.execute('SELECT login FROM game_requests')],['',''])
    def test_request_ownership_uses_identity_even_when_two_providers_share_a_login(self):
        with self.api.db() as db:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('same-name'),'987','Player',time.time()+100))
        identifier=self.ask(token='player-session')['id']
        self.assertEqual(self.api.handle('GET','/v1/me/requests',{}, {},'same-name')['requests'],[])
        rows=self.api.handle('GET','/v1/me/requests',{}, {},'player-session')['requests'];self.assertEqual([r['id'] for r in rows],[identifier])
        with self.api.db() as db:db.execute('UPDATE tokens SET login=? WHERE hash=?',('Renamed',digest('player-session')))
        self.assertEqual([r['id'] for r in self.api.handle('GET','/v1/me/requests',{}, {},'player-session')['requests']],[identifier])
    def test_legacy_requests_remain_admin_visible_without_guessing_their_owner(self):
        import sqlite3
        path=pathlib.Path(self.temp.name)/'legacy.db'
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE game_requests(id TEXT PRIMARY KEY,login TEXT,title TEXT,platform TEXT,details TEXT,state TEXT,note TEXT,created REAL,updated REAL)")
            db.execute('INSERT INTO game_requests VALUES(?,?,?,?,?,?,?,?,?)',('1234abcd','Player','Legacy request','Switch','','new','',1,1))
        api=API(path,client_id='test')
        with api.db() as db:
            db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('player'),'oidc:issuer:player','Player',time.time()+100))
            db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('admin'),'oidc:issuer:admin','Admin',time.time()+100))
        api.admins={'admin'}
        self.assertEqual(api.handle('GET','/v1/me/requests',{}, {},'player')['requests'],[])
        rows=api.handle('GET','/v1/admin/requests',{}, {},'admin')['requests'];self.assertEqual([r['id'] for r in rows],['1234abcd'])
    def test_game_files_links_and_empty_fields_are_rejected(self):
        for kwargs in ({'title':'x'},{'platform':''},{'details':'bajar de https://sitio.example/juego'},{'title':'juego.nsp'},{'details':'magnet:?xt=urn:btih:abc'},{'platform':'Switch .xci'}):
            with self.assertRaises(ValueError):self.ask(**kwargs)
        with self.api.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM game_requests').fetchone()[0],0)
    def test_requests_are_limited_per_client(self):
        for _ in range(5):self.ask(remote='1.2.3.4')
        with self.assertRaises(ValueError):self.ask(remote='1.2.3.4')
        self.ask(remote='5.6.7.8')
    def test_only_administrators_can_list_or_change_requests_and_others_see_no_such_route(self):
        identifier=self.ask(token='player-session')['id']
        for token in ('','player-session','unknown-session'):
            with self.assertRaises(FileNotFoundError):self.api.handle('GET','/v1/admin/requests',{}, {},token)
            with self.assertRaises(FileNotFoundError):self.api.handle('POST','/v1/admin/requests/'+identifier,{}, {'state':'fixed'},token)
        listed=self.api.handle('GET','/v1/admin/requests',{}, {},'owner-session')['requests'];self.assertEqual([r['id'] for r in listed],[identifier]);self.assertEqual(listed[0]['details'],'No abre')
        self.assertTrue(self.api.handle('POST','/v1/admin/requests/'+identifier,{}, {'state':'investigating','note':'Probando'},'owner-session')['ok'])
        self.assertEqual(self.api.handle('GET','/v1/admin/requests',{'state':['new']},{},'owner-session')['requests'],[])
        with self.assertRaises(ValueError):self.api.handle('POST','/v1/admin/requests/'+identifier,{}, {'state':'bogus'},'owner-session')
        with self.assertRaises(FileNotFoundError):self.api.handle('POST','/v1/admin/requests/ffffffff',{}, {'state':'fixed'},'owner-session')
    def test_a_player_sees_only_their_own_requests_and_the_admin_flag_is_reported(self):
        self.ask(title='De Player',token='player-session');self.ask(title='De Owner',token='owner-session')
        mine=self.api.handle('GET','/v1/me/requests',{}, {},'player-session')['requests'];self.assertEqual([r['title'] for r in mine],['De Player']);self.assertNotIn('details',mine[0])
        self.assertEqual(self.api.handle('GET','/v1/me',{}, {},'owner-session'),{'login':'Owner','admin':True});self.assertFalse(self.api.handle('GET','/v1/me',{}, {},'player-session')['admin'])
        with self.assertRaises(PermissionError):self.api.handle('GET','/v1/me/requests',{}, {},'')
    def test_a_github_account_with_the_same_name_is_never_an_administrator_and_a_subject_id_can_be_listed(self):
        self.assertFalse(self.api.handle('GET','/v1/me',{}, {},'github-session')['admin'])
        with self.assertRaises(FileNotFoundError):self.api.handle('GET','/v1/admin/requests',{}, {},'github-session')
        self.api.admins={'sub:sub-player'};self.assertTrue(self.api.handle('GET','/v1/me',{}, {},'player-session')['admin']);self.assertFalse(self.api.handle('GET','/v1/me',{}, {},'owner-session')['admin'])
        self.api.admins=set()
        for token in ('owner-session','player-session','github-session'):
            with self.assertRaises(FileNotFoundError):self.api.handle('GET','/v1/admin/requests',{}, {},token)
    def test_many_different_clients_cannot_flood_the_requests(self):
        for number in range(300):self.ask(remote=f'10.0.{number//250}.{number%250}')
        with self.assertRaises(ValueError):self.ask(remote='10.9.9.9')
    def test_nobody_can_rate_their_own_profile(self):
        with self.api.db() as db:db.execute("INSERT INTO presets VALUES(?,?,?,?,?,?,?,?)",('a'*32,'oidc:aaaa:sub-player','Player','game','eden','{}','approved',time.time()))
        with self.assertRaisesRegex(ValueError,'propio perfil'):self.api.handle('POST','/v1/presets/'+'a'*32+'/feedback',{}, {'rating':5},'player-session')
        self.assertTrue(self.api.handle('POST','/v1/presets/'+'a'*32+'/feedback',{}, {'rating':4},'owner-session')['ok'])

    def test_typed_requests_require_a_github_repository_only_for_ports(self):
        for category in ('port','emulated','native','minecraft'):
            body={'title':'Example game','platform':'PC','details':'Controller does not respond','category':category}
            if category=='port':body['repository']='https://github.com/example/game-port/'
            identifier=self.api.handle('POST','/v1/requests',{},body,'player-session',category)['id']
            row=next(r for r in self.api.handle('GET','/v1/admin/requests',{}, {},'owner-session')['requests'] if r['id']==identifier)
            self.assertEqual(row['category'],category);self.assertEqual(row['repository'],'https://github.com/example/game-port' if category=='port' else '')
        for repository in ('','https://github.com/example/game/releases','https://other.example/example/game','https://github.com/example/game.zip?download=1','https://user:secret@github.com/example/game'):
            with self.assertRaises(ValueError):self.api.handle('POST','/v1/requests',{}, {'title':'Example','platform':'PC','category':'port','repository':repository},remote=repository)

    def test_replies_are_private_persistent_and_read_only_by_the_recipient(self):
        identifier=self.ask(token='player-session')['id']
        mine=lambda:self.api.handle('GET','/v1/me/requests',{}, {},'player-session')
        self.assertEqual(mine()['unread'],0)
        self.api.handle('POST','/v1/admin/requests/'+identifier,{}, {'state':'investigating','note':'Testing the renderer'},'owner-session')
        value=mine();self.assertEqual(value['unread'],1);self.assertEqual(value['requests'][0]['replies'][0]['note'],'Testing the renderer')
        observed=value['requests'][0]['updated']
        with self.assertRaises(FileNotFoundError):self.api.handle('POST','/v1/me/requests/'+identifier+'/read',{}, {'updated':observed},'owner-session')
        self.api.handle('POST','/v1/me/requests/'+identifier+'/read',{}, {'updated':observed},'player-session');self.assertEqual(mine()['unread'],0)
        # A text-only reply keeps the state, and reading an older screen cannot hide it.
        self.api.handle('POST','/v1/admin/requests/'+identifier,{}, {'note':'Try the new Vulkan profile'},'owner-session')
        self.api.handle('POST','/v1/me/requests/'+identifier+'/read',{}, {'updated':observed},'player-session')
        value=mine();self.assertEqual(value['unread'],1);self.assertEqual(value['requests'][0]['state'],'investigating');self.assertEqual(len(value['requests'][0]['replies']),2)
        self.api.handle('POST','/v1/admin/requests/'+identifier,{}, {'state':'fixed'},'owner-session')
        self.assertEqual(mine()['requests'][0]['note'],'Try the new Vulkan profile')
        for bad in ('tomorrow',-1,time.time()+999999):
            with self.assertRaises(ValueError):self.api.handle('POST','/v1/me/requests/'+identifier+'/read',{}, {'updated':bad},'player-session')
    def test_the_owner_notification_carries_only_the_game_and_platform_and_never_blocks_the_request(self):
        self.api.notify_url='https://ntfy.example/deck-library'
        with patch('urllib.request.urlopen') as opened:
            identifier=self.ask(title='Mi juego',platform='Switch',details='dato privado',token='player-session')['id']
        sent=opened.call_args[0][0];self.assertEqual(sent.data.decode(),f'Nueva solicitud {identifier}: Mi juego (Switch)');self.assertNotIn(b'Player',sent.data);self.assertNotIn(b'privado',sent.data)
        self.api.notify_url='https://discord.com/api/webhooks/1/x'
        with patch('urllib.request.urlopen') as opened:self.ask(remote='other')
        payload=json.loads(opened.call_args[0][0].data);self.assertIn('content',payload);self.assertEqual(payload['allowed_mentions'],{'parse':[]})
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):self.assertTrue(self.ask(remote='third')['received'])
        self.api.notify_url='http://insecure.example/x'
        with patch('urllib.request.urlopen') as opened:self.ask(remote='fourth');opened.assert_not_called()

if __name__=='__main__':unittest.main()
