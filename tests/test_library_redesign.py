import io,json,pathlib,tempfile,time,unittest
from unittest.mock import patch
from deck_library.models import Entry,Store
from deck_library.conflicts import analyze
from deck_library import controllers,presets
from deck_library.community import Client
from deck_library.emulator_settings import set_language,inspect_emulator
from community.server import API,digest

class RedesignTests(unittest.TestCase):
    def test_conflicts_respect_platform_and_never_remove_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);a=root/'a.rom';b=root/'b.rom';a.touch();b.touch()
            entries=[Entry('Same',['x'],kind='emulated',platform='Wii',source=str(a),game_id='ABCDEF'),Entry('Other filename',['x'],kind='emulated',platform='Wii',source=str(b),game_id='ABCDEF'),Entry('Same',['x'],kind='emulated',platform='PSP',source=str(a))]
            with patch('deck_library.conflicts.shutil.which',return_value=None):rows=analyze(entries,home=root)
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['paths'],[str(a),str(b)]);self.assertTrue(a.exists() and b.exists())
    def test_one_symlink_is_not_reported_as_two_rom_copies(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);a=root/'a';a.touch();b=root/'b';b.symlink_to(a)
            entries=[Entry('Game',['x'],kind='emulated',platform='Wii',source=str(p)) for p in (a,b)]
            with patch('deck_library.conflicts.shutil.which',return_value=None):rows=analyze(entries,home=root)
            self.assertEqual(rows[0]['kind'],'entry')
    def test_self_shortcut_has_valid_stable_identity_and_is_not_a_game(self):
        from deck_library.library_app import entry
        from deck_library.library_view import visible_entries
        a=entry('/tmp/first/app.py');b=entry('/tmp/second/app.py');self.assertEqual(a.id,b.id);self.assertIn('--gaming',a.command);self.assertEqual(visible_entries([a])[0],[])
    def test_library_layout_keeps_native_sticks_and_puts_mouse_on_trackpad_only(self):
        from deck_library.steam_input import parse_text,first
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            base='"controller_mappings" { "group" { "id" "3" "mode" "joystick_move" } "group" { "id" "8" "mode" "joystick_move" } "preset" { "group_source_bindings" { "3" "joystick active" "8" "right_joystick active" "8" "right_trackpad active" } } }'
            (root/'controller_neptune_gamepad_joystick.vdf').write_text(base)
            with patch('deck_library.controllers.templates_dir',return_value=root):name=controllers.library_template(root)
            value=first(parse_text((root/name).read_text()),'controller_mappings',[]);groups=[v for k,v in value if k=='group'];bindings=first(first(value,'preset',[]),'group_source_bindings',[])
            self.assertEqual([first(g,'mode') for g in groups],['joystick_move','joystick_move','absolute_mouse']);self.assertIn(('3','joystick active'),bindings);self.assertIn(('8','right_joystick active'),bindings);self.assertIn(('9','right_trackpad active'),bindings);self.assertNotIn(('8','right_trackpad active'),bindings)
            self.assertEqual((root/'controller_neptune_gamepad_joystick.vdf').read_text(),base)
            legacy='legacy keyboard template';(root/name).write_text(legacy)
            with patch('deck_library.controllers.templates_dir',return_value=root):controllers.library_template(root);controllers.library_template(root)
            backups=list(root.glob(name+'.deck-library-backup-*'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(),legacy)
    def test_client_rejects_plaintext_and_embedded_credentials(self):
        for url in ('http://example.org','https://user:secret@example.org','https://example.org?token=x'):
            with self.assertRaises(ValueError):Client(Store('/tmp/unused-community-test'),url)
    def test_eden_language_is_backed_up_without_touching_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);store=Store(root/'data');config=root/'eden';config.mkdir();(config/'qt-config.ini').write_text('[System]\nlanguage_index=1\n[Controls]\nprofile_name=My pad\n')
            e=Entry('Test',['x'],kind='emulated',platform='Switch',game_id='0100000000000000');prefs={'eden_config':str(config)}
            self.assertEqual(inspect_emulator(e,prefs)['language'],'1')
            with patch('deck_library.presets.busy',return_value=False):set_language(e,'14',store,prefs)
            self.assertEqual(inspect_emulator(e,prefs)['language'],'14');self.assertIn('My pad',(config/'qt-config.ini').read_text());self.assertTrue(list((store.root/'preset-backups').rglob('original')))

class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.api=API(pathlib.Path(self.temp.name)/'test.db',client_id='public-id',review_required=True);self.value=json.loads((pathlib.Path(__file__).resolve().parent.parent/'presets/eden-switch-performance.json').read_text());self.token='local-test-token'
        with self.api.db() as db:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest(self.token),'1','VerifiedUser',time.time()+500))
    def tearDown(self):self.temp.cleanup()
    def request(self,method,path,body=None,token=''):
        return self.api.handle(method,path,{},body or {},token)
    def test_public_read_and_login_required_for_writes(self):
        self.assertEqual(self.request('GET','/v1/presets'),{'presets':[]})
        with self.assertRaises(PermissionError):self.request('POST','/v1/presets',self.value)
    def test_publish_is_moderated_and_author_cannot_be_spoofed(self):
        result=self.request('POST','/v1/presets',self.value,self.token);self.assertEqual(result['status'],'pending');self.assertEqual(self.request('GET','/v1/presets')['presets'],[])
        with self.api.db() as db:db.execute("UPDATE presets SET status='approved' WHERE id=?",(result['id'],))
        row=self.request('GET','/v1/presets')['presets'][0];self.assertEqual(row['preset']['author'],'VerifiedUser');self.assertEqual(row['id'],result['id'])
    def test_private_pending_contributions_belong_only_to_their_user(self):
        self.request('POST','/v1/presets',self.value,self.token)
        rows=self.request('GET','/v1/me/presets',token=self.token)['presets'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'pending')
        with self.api.db() as db:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('other'),'2','OtherUser',time.time()+500))
        self.assertEqual(self.request('GET','/v1/me/presets',token='other')['presets'],[])
        with self.assertRaises(PermissionError):self.request('GET','/v1/me/presets')
    def test_unsafe_profile_and_invalid_feedback_rejected(self):
        self.value['settings']['Renderer']['execute']='rm -rf anything'
        with self.assertRaises(ValueError):self.request('POST','/v1/presets',self.value,self.token)
        with self.assertRaises(ValueError):self.request('POST','/v1/presets/'+'a'*32+'/feedback',{'result':'works'},self.token)
    def test_feedback_one_record_per_user_and_logout(self):
        r=self.request('POST','/v1/presets',self.value,self.token)
        with self.api.db() as db:db.execute("UPDATE presets SET status='approved'")
        # The author cannot rate their own profile, so a second account gives the feedback.
        from community.server import digest
        import time
        with self.api.db() as db:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('other-token'),'other-user','Other',time.time()+100))
        with self.assertRaises(ValueError):self.request('POST','/v1/presets/'+r['id']+'/feedback',{'result':'works'},self.token)
        for status in ('works','issues'):self.request('POST','/v1/presets/'+r['id']+'/feedback',{'result':status},'other-token')
        with self.api.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM feedback').fetchone()[0],1)
        self.request('POST','/v1/logout',token=self.token)
        with self.assertRaises(PermissionError):self.api.session(self.token)
    def test_expired_session_rejected(self):
        with self.api.db() as db:db.execute('UPDATE tokens SET expires=0')
        with self.assertRaises(PermissionError):self.api.session(self.token)
    def test_device_login_isolated_and_poll_interval_honored(self):
        responses=[{'device_code':'github-private','user_code':'ABCD-EFGH','interval':5,'expires_in':900},{'access_token':'ephemeral-github-token'},{'id':2,'login':'ActualUser'}]
        with patch('community.server.github',side_effect=responses) as mock:
            start=self.request('POST','/v1/auth/start');self.assertNotIn('device_code',start)
            pending=self.request('POST','/v1/auth/poll',{'wait_key':start['wait_key']});self.assertEqual(pending['state'],'pending');self.assertEqual(mock.call_count,1)
            with self.api.db() as db:db.execute('UPDATE devices SET next_poll=0')
            connected=self.request('POST','/v1/auth/poll',{'wait_key':start['wait_key']});self.assertEqual(self.api.session(connected['token'])['login'],'ActualUser')
            with self.assertRaises(ValueError):self.request('POST','/v1/auth/poll',{'wait_key':start['wait_key']})
    def test_wsgi_invalid_size_and_private_errors(self):
        statuses=[];raw=b'{"no":"matter"}'
        result=self.api({'REQUEST_METHOD':'POST','PATH_INFO':'/v1/presets','CONTENT_LENGTH':'999999','CONTENT_TYPE':'application/json','wsgi.input':io.BytesIO(raw)},lambda status,headers:statuses.append(status))
        self.assertTrue(statuses[0].startswith('400'));self.assertNotIn(self.token,b''.join(result).decode())
    def test_client_download_uses_community_namespace(self):
        e=Entry('Switch',['x'],platform='Switch',game_id=self.value['game']['id'])
        store=Store(pathlib.Path(self.temp.name)/'client');c=Client(store,'https://presets.example.org');value=c.download({'id':'a'*32,'preset':self.value});self.assertTrue(value['id'].startswith('community-'));self.assertTrue((store.root/'presets'/(value['id']+'.json')).exists())
