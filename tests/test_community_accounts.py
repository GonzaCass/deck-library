"""Account migration, device authorization and real community votes."""
import json,pathlib,sqlite3,tempfile,time,unittest
from unittest.mock import Mock,patch
from community.server import API,digest
from community.oidc import DeviceAuth
from deck_library.models import Store,atomic_json
from deck_library import updates
from deck_library.gamepad import Repeater
from deck_library.transfer import Progress,caption

class AccountsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.temp.name)/'community.db';self.api=API(self.path,client_id='public-test')
    def tearDown(self):self.temp.cleanup()
    def test_own_account_device_tokens_remain_on_server_and_replay_fails(self):
        provider=Mock(issuer='https://auth.example.org/realms/public')
        provider.start.return_value={'device_code':'provider-private-code','user_code':'ABCD','verification_uri':'https://auth.example.org/device','interval':5,'expires_in':600}
        provider.poll.return_value={'access_token':'provider-private-token'};provider.user.return_value=('subject','Player')
        self.api.oidc=provider
        start=self.api.handle('POST','/v1/auth/start',{}, {'provider':'keycloak'})
        self.assertNotIn('device_code',start)
        self.assertEqual(self.api.handle('POST','/v1/auth/poll',{}, {'wait_key':start['wait_key']})['state'],'pending');provider.poll.assert_not_called()
        with self.api.db() as db:db.execute('UPDATE devices SET next_poll=0')
        connected=self.api.handle('POST','/v1/auth/poll',{}, {'wait_key':start['wait_key']})
        self.assertNotIn('provider-private',json.dumps(connected));self.assertEqual(self.api.session(connected['token'])['login'],'Player')
        self.assertTrue(self.api.session(connected['token'])['uid'].startswith('oidc:'))
        with self.assertRaises(ValueError):self.api.handle('POST','/v1/auth/poll',{}, {'wait_key':start['wait_key']})
    def test_seeded_modes_and_one_real_vote_per_user(self):
        query={'game':['01006a800016e000'],'adapter':['eden']}
        rows=self.api.handle('GET','/v1/presets',query,{})['presets']
        self.assertGreaterEqual(len(rows),4);self.assertTrue(all(r['ratings']==0 and r['rating'] is None for r in rows))
        self.assertTrue(all(r['preset']['game']['id'].lower()==query['game'][0] for r in rows))
        identifier=rows[0]['id'];path='/v1/presets/'+identifier+'/feedback'
        with self.api.db() as db:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('session'),'tester','TestPlayer',time.time()+100))
        with self.assertRaises(PermissionError):self.api.handle('POST',path,{}, {'rating':5})
        for invalid in (True,0,6,'5'):
            with self.assertRaises(ValueError):self.api.handle('POST',path,{}, {'rating':invalid},'session')
        for rating in (2,4):self.api.handle('POST',path,{}, {'rating':rating,'notes':'My test'},'session')
        row=next(r for r in self.api.handle('GET','/v1/presets',query,{})['presets'] if r['id']==identifier)
        self.assertEqual((row['ratings'],row['rating']),(1,4))
        comments=self.api.handle('GET',path,{}, {})['comments'];self.assertEqual(len(comments),1);self.assertEqual(comments[0]['author'],'TestPlayer')
    def test_discovery_rejects_wrong_issuer_and_cross_origin_tokens(self):
        provider=DeviceAuth('https://auth.example.org/realms/public','desktop')
        with patch('community.oidc.request',return_value={'issuer':'https://other.example.org'}),self.assertRaises(ValueError):provider.endpoints()
        endpoints={'issuer':provider.issuer,**{k:'https://auth.example.org/'+k for k in ('device_authorization_endpoint','token_endpoint','userinfo_endpoint')}}
        endpoints['token_endpoint']='https://other.example.org/token'
        with patch('community.oidc.request',return_value=endpoints),self.assertRaises(ValueError):provider.endpoints()
    def test_legacy_database_migration_preserves_sessions_and_comments(self):
        with self.api.db() as db:
            db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('legacy'),'old','OldPlayer',time.time()+100))
            db.execute('ALTER TABLE feedback DROP COLUMN rating');db.execute('ALTER TABLE feedback DROP COLUMN author');db.execute('ALTER TABLE devices DROP COLUMN provider')
        migrated=API(self.path,client_id='public-test');self.assertEqual(migrated.session('legacy')['login'],'OldPlayer')
        with migrated.db() as db:self.assertIn('rating',{r['name'] for r in db.execute('PRAGMA table_info(feedback)')})

class ProgressAndInputTests(unittest.TestCase):
    def test_measured_download_eta_and_work_phases(self):
        progress=Progress();progress.update({'phase':'download','done':0,'total':100},now=0)
        state=progress.update({'phase':'download','done':25,'total':100},now=5)
        self.assertEqual(state['fraction'],.25);self.assertEqual(state['eta'],15);self.assertIn('25%',caption(state))
        state=progress.update('Compilando');self.assertIsNone(state['eta']);self.assertIsNone(state['fraction'])
        state=progress.update({'phase':'download','done':40,'total':0},now=6);self.assertIsNone(state['eta']);self.assertIsNone(state['fraction'])
    def test_controller_press_and_repeat_do_not_repeat_activation(self):
        keys=Repeater();self.assertEqual(keys.events({'activate','down'},now=0),['activate','down'])
        self.assertEqual(keys.events({'activate','down'},now=.2),[])
        self.assertEqual(keys.events({'activate','down'},now=.36),['down'])
        self.assertEqual(keys.events(set(),now=.4),[]);self.assertEqual(keys.events({'activate'},now=.5),['activate'])
    def test_completed_port_removes_only_obsolete_update_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(pathlib.Path(tmp));atomic_json(store.root/'ports.json',{'example/game':{'tag':'v3'}})
            atomic_json(updates.cache_path(store),{'checked':time.time(),'catalog':[{'repository':'example/game','latest':'v3'},{'repository':'example/other','latest':'v4'}]})
            self.assertEqual([r['repository'] for r in updates.cached(store)['catalog']],['example/other'])
            self.assertEqual(len(json.loads(updates.cache_path(store).read_text())['catalog']),1)
