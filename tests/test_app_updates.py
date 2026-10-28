import io,pathlib,tempfile,time,unittest,urllib.error
from unittest.mock import patch
from deck_library import __version__,library_app,ports,runtime,updates
from deck_library.models import Entry,Store,atomic_json

def release(version='99.0.0'):
    name='DeckLibrary-'+version+'.tar.gz';base='https://github.com/'+updates.REPO+'/releases/download/v'+version+'/'
    return {'tag_name':'v'+version,'assets':[{'name':name,'browser_download_url':base+name},{'name':name+'.sha256','browser_download_url':base+name+'.sha256'}]}

class AppUpdatesTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'private')
    def tearDown(self):self.temp.cleanup()

    def test_an_inflight_check_cannot_restore_an_offer_for_a_port_just_installed(self):
        row={'name':'Game','repository':'Example/Port','installed':'v1','latest':'v2'}
        state={'catalog':[row],'ports':[row],'app':None}
        atomic_json(self.store.root/'ports.json',{'example/port':{'tag':'v2'}})
        reconciled=updates.reconcile_ports(state,self.store)
        self.assertEqual(reconciled['catalog'],[]);self.assertEqual(reconciled['ports'],[])
        self.assertEqual(len(state['catalog']),1)
        atomic_json(self.store.root/'ports.json',{'example/port':{'tag':'v1'}})
        self.assertEqual(updates.reconcile_ports(state,self.store)['catalog'],[row])

    def test_upgrading_the_app_invalidates_its_own_check_without_rescanning_ports(self):
        now=time.time();atomic_json(updates.cache_path(self.store),{'checked':now,'app_checked':now,'app_checked_version':'old','app':None})
        calls=[]
        def get(url):calls.append(url);return release()
        with patch.object(ports,'installed_updates',side_effect=AssertionError('ports were not due')):
            state=updates.check_all(self.store,{'catalog_auto':False},[],get=get)
        self.assertEqual(state['app']['version'],'99.0.0');self.assertEqual(len(calls),1)
        updates.check_all(self.store,{},[],get=get);self.assertEqual(len(calls),1)

    def test_the_app_offer_is_delivered_before_slow_port_checks(self):
        observed=[]
        def port_check(*_):
            self.assertEqual(observed[0]['app']['version'],'99.0.0');return []
        with patch.object(updates,'check_quiver',return_value=[]),patch.object(ports,'installed_updates',side_effect=port_check),patch('deck_library.wiiupdate.check',return_value=None):
            state=updates.check_all(self.store,{'catalog_auto':False},[],force=True,get=lambda _:release(),on_app=observed.append)
        self.assertEqual(len(observed),1);self.assertEqual(state['app']['version'],'99.0.0')

    def test_api_failure_can_use_a_verified_github_release_redirect(self):
        def forbidden(url):raise urllib.error.HTTPError(url,403,'Forbidden',{},None)
        info=updates.check_app('1.0.0',forbidden,fallback=release)
        self.assertEqual(info['version'],'99.0.0');self.assertTrue(info['checksum'].endswith('.tar.gz.sha256'))
        with self.assertRaises(urllib.error.HTTPError):updates.latest_release(updates.REPO,forbidden)
        for url,accepted in [('https://github.com/'+updates.REPO+'/releases/tag/v99.0.0',True),('https://example.com/releases/tag/v99.0.0',False),('https://github.com/other/repo/releases/tag/v99.0.0',False)]:
            response=io.BytesIO();response.url=url
            with patch('urllib.request.urlopen',return_value=response):
                if accepted:self.assertEqual(updates.web_release()['tag_name'],'v99.0.0')
                else:
                    with self.assertRaises(ValueError):updates.web_release()

    def test_failed_checks_remain_visible_and_do_not_erase_a_known_offer(self):
        atomic_json(updates.cache_path(self.store),{'checked':time.time(),'app':{'version':'99.0.0'}})
        def offline(_):raise OSError('offline')
        state=updates.check_all(self.store,{},[],get=offline)
        self.assertEqual(state['app']['version'],'99.0.0');self.assertIn('offline',state['app_error']);self.assertTrue(state['errors'])
        calls=[]
        state=updates.check_all(self.store,{},[],get=lambda url:(calls.append(url),release())[1]);self.assertEqual(calls,[])
        state['app_checked']-=61;atomic_json(updates.cache_path(self.store),state)
        recovered=updates.check_all(self.store,{},[],get=lambda _:release());self.assertNotIn('app_error',recovered)

    def test_existing_steam_self_launcher_moves_to_the_installed_copy_without_changing_steam(self):
        old_app=self.root/'Downloads/OldVersion/app.py';new_app=self.root/'Applications/DeckLibrary/app.py'
        old=library_app.entry(old_app);old.metadata.update(steam_appid=123456,steam_account='kept');old.cover='chosen-cover.png'
        game=Entry('Other game',['/bin/true']);self.store.save([old,game]);path=runtime.make_launcher(old,self.store,app=old_app)
        with patch('deck_library.steam.find_accounts',return_value=[self.root/'account']),patch.object(library_app,'managed_shortcuts',return_value=[{'appid':123456}]):
            self.assertTrue(library_app.refresh_existing_launcher(self.store,app=new_app))
        current=next(e for e in self.store.load() if e.id==library_app.APP_ID)
        self.assertEqual(current.source,str(new_app));self.assertIn(str(new_app),current.command)
        self.assertEqual(current.metadata['steam_appid'],123456);self.assertEqual(current.cover,'chosen-cover.png')
        self.assertIn(str(new_app),path.read_text());self.assertNotIn(str(old_app),path.read_text())
        self.assertIn(str(old_app),path.with_suffix('.sh.before-upgrade').read_text());self.assertEqual(len(self.store.load()),2)

if __name__=='__main__':unittest.main()
