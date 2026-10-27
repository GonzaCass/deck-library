import os,pathlib,subprocess,tempfile,unittest
from unittest.mock import patch
from deck_library import steam_sync,service
from deck_library.models import Store,Entry

class DurableSteamSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=pathlib.Path(self.tmp.name);self.store=Store(self.home/'User data')
    def test_installer_persists_watcher_and_orders_recovery_before_steam(self):
        folder=steam_sync.install(self.store,app=self.home/'Application/App.py',home=self.home,activate=False)
        self.assertTrue((folder/'default.target.wants/deck-library-sync.path').is_file())
        self.assertIn('PathExists='+str(self.store.root/'pending.json'),(folder/'deck-library-sync.path').read_text())
        self.assertIn('--before-steam',(folder/'deck-library-before-steam.service').read_text())
        self.assertIn('Before=steam-launcher.service gamescope-session.service graphical-session-pre.target',(folder/'deck-library-before-steam.service').read_text())
        self.assertIn('Restart=on-failure',(folder/'deck-library-sync.service').read_text())
        # Existing units are updated without replacing unrelated user drop-ins.
        custom=folder/'steam-launcher.service.d/personal.conf';custom.parent.mkdir(exist_ok=True);custom.write_text('[Service]\nEnvironment=MY_CUSTOM=1\n')
        steam_sync.install(self.store,app=self.home/'New app/app.py',home=self.home,activate=False)
        self.assertIn('New app/app.py',(folder/'deck-library-sync.service').read_text());self.assertTrue(custom.exists())
    def test_queue_from_previous_boot_is_applied_without_opening_the_gui(self):
        cfg=self.home/'Steam/config';cfg.mkdir(parents=True);entry=Entry('Naruto',['/bin/true'])
        with patch.object(service,'steam_running',return_value=True):service.queue_entries([entry],cfg,self.store,start_worker=False)
        # Simulate a new invocation before Steam starts: durable JSON is the only state.
        with patch.object(service,'steam_running',return_value=False),patch('deck_library.steam.steam_running',return_value=False):
            result=steam_sync.before_steam(Store(self.store.root))
        self.assertEqual(result['state'],'saved');self.assertFalse((self.store.root/'pending.json').exists())
        from deck_library.steam_inventory import shortcuts
        self.assertEqual(shortcuts(cfg)[0]['name'],'Naruto')
    def test_startup_leaves_steam_open_and_preserves_queue_if_client_already_running(self):
        cfg=self.home/'Steam/config';cfg.mkdir(parents=True)
        with patch.object(service,'steam_running',return_value=True),patch('deck_library.steam.steam_running',return_value=True):
            service.queue_entries([Entry('Game',['/bin/true'])],cfg,self.store,start_worker=False)
            result=steam_sync.before_steam(self.store)
        self.assertEqual(result['state'],'pending');self.assertFalse((cfg/'shortcuts.vdf').exists())
    def test_recovery_waits_for_an_existing_writer_instead_of_losing_race_to_steam(self):
        with patch.object(service,'sync',side_effect=[{'state':'pending'},{'state':'saved'}]) as sync,patch('deck_library.steam.steam_running',return_value=False),patch.object(steam_sync.time,'sleep'):
            self.assertEqual(steam_sync.before_steam(self.store)['state'],'saved');self.assertEqual(sync.call_count,2)
    def test_manager_bus_fix_does_not_change_graphical_environment(self):
        original={'XDG_RUNTIME_DIR':'/remote-session','DBUS_SESSION_BUS_ADDRESS':'unix:path=/remote/bus','DISPLAY':':10'}
        with patch.dict(os.environ,original):
            env=steam_sync.manager_environment();self.assertEqual(env['DISPLAY'],':10');self.assertEqual(os.environ['XDG_RUNTIME_DIR'],'/remote-session')
        if pathlib.Path('/run/user',str(os.getuid()),'bus').is_socket():self.assertEqual(env['XDG_RUNTIME_DIR'],'/run/user/'+str(os.getuid()))
    def test_systemctl_is_not_called_for_another_library(self):
        steam_sync.install(self.store,app=self.home/'app.py',home=self.home,activate=False)
        with patch.object(pathlib.Path,'home',return_value=self.home),patch.object(steam_sync.subprocess,'run') as run:
            self.assertFalse(steam_sync.start(Store(self.home/'different')));run.assert_not_called()
    def test_existing_store_uses_the_persistent_watcher(self):
        steam_sync.install(self.store,app=self.home/'app.py',home=self.home,activate=False)
        with patch.object(pathlib.Path,'home',return_value=self.home),patch.object(steam_sync.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')) as run,patch.object(steam_sync.shutil,'which',return_value='/usr/bin/systemctl'):
            self.assertTrue(steam_sync.start(self.store))
            self.assertEqual(run.call_args.args[0][-1],'deck-library-sync.path')

    def test_systemd_start_failure_is_reported(self):
        with patch.object(steam_sync.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'No bus')),patch.object(steam_sync.shutil,'which',return_value='/usr/bin/systemctl'):
            with self.assertRaisesRegex(RuntimeError,'No bus'):steam_sync.install(self.store,app=self.home/'app.py',home=self.home)
