import hashlib,json,pathlib,shutil,tempfile,unittest
from unittest.mock import patch
from deck_library import library_app,service,steam,steamart
from deck_library.models import Store
from deck_library.runtime import make_launcher

class LibraryArtworkUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name)
        self.store=Store(self.root/'private');self.account=self.root/'steam/config';self.app=self.root/'app/app.py';self.app.parent.mkdir();self.app.write_text('')
        self.base=self.app.parent/'assets/steam';shutil.copytree(pathlib.Path(library_app.__file__).parent.parent/'assets/steam',self.base)
        entry=library_app.entry(self.app);self.store.save([entry]);launcher=make_launcher(entry,self.store)
        result,_=steam.update_shortcuts(self.account,[entry],lambda _:launcher,is_running=lambda:False);self.appid=result[0]['appid']
        self.grid=self.account/'grid';self.grid.mkdir(exist_ok=True)
        self.paths={slot:self.grid/(str(self.appid)+steamart.SLOTS[slot][0]+'.png') for slot in library_app.ART_FILES}
        for slot,path in self.paths.items():shutil.copy2(self.base/library_app.ART_FILES[slot],path)
        self.old=b'\x89PNG\r\n\x1a\nprevious bundled image';self.paths['portrait'].write_bytes(self.old)
        (self.base/'previous-defaults.json').write_text(json.dumps({'schema':1,'slots':{'portrait':[hashlib.sha256(self.old).hexdigest()]}}))

    def test_upgrade_refreshes_known_art_with_backups_and_keeps_custom_art_and_shortcut(self):
        custom=b'\x89PNG\r\n\x1a\ncustom hero';self.paths['hero'].write_bytes(custom);self.paths['banner'].unlink()
        shortcut=(self.account/'shortcuts.vdf').read_bytes()
        with patch.object(steam,'find_accounts',return_value=[self.account]),patch.object(service,'steam_running',return_value=True):
            count=library_app.refresh_existing_art(self.store,app=self.app,start_worker=False)
        self.assertEqual(count,2);self.assertEqual(self.paths['portrait'].read_bytes(),self.old)
        queued=json.loads((self.store.root/'pending.json').read_text());self.assertEqual({i['slot'] for i in queued['art']},{'portrait','banner'})
        with patch.object(service,'steam_running',return_value=False):self.assertEqual(service.sync(self.store,wait=False)['art'],2)
        self.assertEqual(self.paths['portrait'].read_bytes(),(self.base/'portrait.png').read_bytes())
        self.assertEqual(self.paths['hero'].read_bytes(),custom);self.assertEqual((self.account/'shortcuts.vdf').read_bytes(),shortcut)
        self.assertTrue(any(p.read_bytes()==self.old for p in (self.grid/'.deck-library-backups').iterdir()))
        with patch.object(steam,'find_accounts',return_value=[self.account]):self.assertEqual(library_app.refresh_existing_art(self.store,app=self.app,start_worker=False),0)
        self.assertFalse((self.store.root/'pending.json').exists())

    def test_an_explicit_queued_choice_wins_even_if_migration_saw_an_older_snapshot(self):
        choice=steamart.stage(self.store,self.appid,'portrait',b'\x89PNG\r\n\x1a\nchosen by user','.png')
        manual={'appid':self.appid,'slot':'portrait','file':choice}
        with patch.object(service,'steam_running',return_value=True):service.queue_art([manual],self.account,self.store,start_worker=False)
        self.assertEqual(library_app.art_items(self.account,self.store,self.app),[])
        stale={'appid':self.appid,'slot':'portrait','file':str(self.base/'portrait.png')}
        with patch.object(steam,'find_accounts',return_value=[self.account]),patch.object(service,'steam_running',return_value=True),patch.object(library_app,'art_items',return_value=[stale]):
            library_app.refresh_existing_art(self.store,app=self.app,start_worker=False)
        queued=json.loads((self.store.root/'pending.json').read_text());self.assertEqual(queued['art'],[manual])
        self.assertEqual(pathlib.Path(choice).read_bytes(),b'\x89PNG\r\n\x1a\nchosen by user')

    def test_a_missing_or_invalid_history_never_replaces_existing_art(self):
        history=self.base/'previous-defaults.json'
        for contents in (None,'{bad json','[]','{"schema":1,"slots":[]}'):
            if contents is None:history.unlink(missing_ok=True)
            else:history.write_text(contents)
            self.assertEqual(library_app.art_items(self.account,self.store,self.app),[])
        self.assertEqual(self.paths['portrait'].read_bytes(),self.old)
