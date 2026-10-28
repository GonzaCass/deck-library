import copy,json,os,pathlib,secrets,tempfile,time,unittest,urllib.parse,zipfile
from unittest.mock import patch
from deck_library import bug_report,validated_games,presets
from deck_library.models import Store,Entry
from community.server import API,digest,client_address

class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data');self.entry=Entry('Game',['/bin/true'],source=str(self.root/'game.exe'));self.store.root.mkdir()
    def report(self):
        r=bug_report.collect(self.store,self.entry);r.update(title='Game fails',description='1. Open game\nExpected: game\nActual: error');return r
    def test_bounded_logs_are_sanitized_and_configs_roms_symlinks_are_excluded(self):
        (self.store.root/'logs').mkdir();(self.root/'logs').mkdir()
        private='Authorization: Bearer SECRETBEARER\npassword="SECRETPASS"\ntoken=SECRETTOKEN\n/home/private/.local/share/Steam/userdata/12345/config\nmail@example.org\nhttps://auth.example/device?session_code=SECRETSESSION\n'
        (self.store.root/'logs'/(self.entry.id+'.log')).write_text('x'*40000+private)
        (self.root/'game.iso').write_text('ROMSECRET');(self.root/'settings.ini').write_text('SECRETCONFIG')
        (self.root/'logs/leak.log').symlink_to(self.root/'settings.ini');(self.root/'logs/game.log').write_text('frame time 16ms')
        with patch.dict(os.environ,{'PASSWORD':'ENVSECRET'}):value=self.report()
        text=json.dumps(value)
        for word in ('SECRETBEARER','SECRETPASS','SECRETTOKEN','SECRETSESSION','mail@example.org','/home/private','userdata/12345','ROMSECRET','SECRETCONFIG','ENVSECRET'):self.assertNotIn(word,text)
        self.assertEqual(len(value['files']),2);self.assertLess(len(value['files'][0]['text']),bug_report.MAX_LOG+1)
        self.assertFalse(bug_report.collect(self.store,self.entry,include_logs=False)['files'])
    def test_export_is_private_valid_json_and_issue_draft_omits_raw_logs(self):
        report=self.report();report['description']='Open /home/alice/game then mail alice@example.org';report['files']=[{'name':'game.log','text':'token="SECRET"'}]
        path=bug_report.export(report,self.root/'report.zip');self.assertEqual(path.stat().st_mode&0o777,0o600)
        with zipfile.ZipFile(path) as archive:
            data=json.loads(archive.read('report.json'));self.assertNotIn('SECRET',archive.read('game.log').decode());self.assertEqual(set(archive.namelist()),{'report.json','summary.txt','game.log'})
        query=urllib.parse.parse_qs(urllib.parse.urlsplit(bug_report.issue_url(data,'abc123')).query);self.assertIn('abc123',query['body'][0]);self.assertNotIn('SECRET',query['body'][0]);self.assertNotIn('/home/alice',query['body'][0])
    def test_invalid_report_paths_and_missing_problem_are_rejected(self):
        value=self.report();value['files']=[{'name':'../config.log','text':'x'}]
        with self.assertRaises(ValueError):bug_report.validate_report(value)
        value=self.report();value['files']=[{'name':12,'text':'x'}]
        with self.assertRaises(ValueError):bug_report.validate_report(value)
        value=self.report();value['description']=''
        with self.assertRaises(ValueError):bug_report.validate_report(value)

class CommunityPublicationTests(unittest.TestCase):
    def test_rate_limits_use_forwarded_clients_only_from_an_explicit_trusted_proxy(self):
        import ipaddress
        trusted=(ipaddress.ip_network('192.0.2.0/24'),)
        request={'REMOTE_ADDR':'192.0.2.10','HTTP_X_REAL_IP':'198.51.100.12'}
        self.assertEqual(client_address(request,trusted),'198.51.100.12')
        self.assertEqual(client_address(request),'192.0.2.10')
        self.assertEqual(client_address({**request,'REMOTE_ADDR':'203.0.113.1'},trusted),'203.0.113.1')
        self.assertEqual(client_address({**request,'HTTP_X_REAL_IP':'not-an-address'},trusted),'192.0.2.10')
        self.assertEqual(client_address({**request,'HTTP_X_REAL_IP':'198.51.100.12, 198.51.100.13'},trusted),'192.0.2.10')

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.api=API(self.root/'community.db',client_id='test',review_required=False)
        with self.api.db() as db:
            for user in ('one','two'):db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest(user),user,user,time.time()+60))
        self.profile=next(p for p in presets.catalog(Store(self.root/'empty')) if p['id']=='narutorise-deck-balanced');self.profile={**self.profile,'id':'community-test-profile','author':'spoofed','tested':{'status':'proposal','date':'2026-10-27'}}
    def test_a_new_profile_and_another_users_comment_are_public_and_scoped(self):
        value=self.api.handle('POST','/v1/presets',{},self.profile,'one');self.assertEqual(value['status'],'approved')
        query={'game':['555307e5'],'adapter':['narutorise']};rows=self.api.handle('GET','/v1/presets',query,{})['presets'];row=next(r for r in rows if r['id']==value['id']);self.assertEqual(row['author'],'one');self.assertEqual(row['preset']['author'],'one')
        path='/v1/presets/'+value['id']+'/feedback';self.api.handle('POST',path,{}, {'rating':4,'notes':'Works on another Deck'},'two')
        self.assertEqual(self.api.handle('GET',path,{}, {})['comments'][0]['author'],'two')
        row=next(r for r in self.api.handle('GET','/v1/presets',query,{})['presets'] if r['id']==value['id']);self.assertEqual((row['ratings'],row['rating']),(1,4))
        self.assertFalse(self.api.handle('GET','/v1/presets',{'game':['different'],'adapter':['narutorise']},{})['presets'])
    def test_review_mode_retains_explicit_pending_visibility(self):
        self.api.review_required=True;result=self.api.handle('POST','/v1/presets',{},self.profile,'one');self.assertEqual(result['status'],'pending')
        query={'game':['555307e5'],'adapter':['narutorise']};self.assertFalse(any(r['id']==result['id'] for r in self.api.handle('GET','/v1/presets',query,{})['presets']))
        self.assertEqual(self.api.handle('GET','/v1/me/presets',query,{},'one')['presets'][0]['status'],'pending')
    def test_diagnostics_are_explicit_anonymous_private_and_redacted(self):
        value=bug_report.collect(Store(self.root/'empty'));value.update(title='Startup problem',description='password="SECRET" at /home/testuser/game')
        result=self.api.handle('POST','/v1/bug-reports',{},value);self.assertTrue(result['received'])
        with self.api.db() as db:
            row=db.execute('SELECT body FROM bug_reports WHERE id=?',(result['id'],)).fetchone();report=json.loads(row['body']);self.assertNotIn('SECRET',row['body']);self.assertNotIn('/home/testuser',report['description'])
        with self.assertRaises(FileNotFoundError):self.api.handle('GET','/v1/bug-reports/'+result['id'],{}, {})

class ValidatedGamesTests(unittest.TestCase):
    def test_every_entry_has_gameplay_evidence_and_never_claims_installation_is_a_game_test(self):
        rows=validated_games.catalog();self.assertEqual(len(rows),7)
        names={row['name'] for row in rows};self.assertIn('Naruto: Rise of a Ninja',names);self.assertIn('Grand Theft Auto IV',names);self.assertIn('Spider-Man: Shattered Dimensions',names)
        for row in rows:self.assertTrue(row['result']);self.assertTrue(row['limitations']);self.assertTrue(row['version']);self.assertTrue(row['fix']);self.assertTrue(row['fix_evidence']);self.assertIn(row['fix_how'],validated_games.FIX_HOW)
        port=Entry('Naruto',['port'],metadata={'port_repository':'jorjbarbosa/naruto-rise-recomp'})
        row=next(r for r in rows if r['id']=='narutorise-v03');self.assertEqual(validated_games.matching(row,[port]),port)
        other=Entry('Naruto',['port'],metadata={'port_repository':'other/naruto'})
        self.assertIsNone(validated_games.matching(row,[other]))
