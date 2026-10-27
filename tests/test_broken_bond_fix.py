import io,json,pathlib,tempfile,tomllib,unittest,zipfile
from unittest.mock import patch
from deck_library import broken_bond,ports,proton_tools,port_removal,original_data,port_runtime,project2099
from deck_library.models import Store,Entry,atomic_json
from test_naruto_ports import xex


class BrokenBondFixTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'private');self.ports=self.root/'ports';self.folder=self.ports/'old-broken';self.folder.mkdir(parents=True)
        (self.folder/'game').mkdir();xex(self.folder/'game/default.xex');(self.folder/'user').mkdir();(self.folder/'user/save.dat').write_text('progress');(self.folder/'broken_bond_launcher.exe').write_bytes(b'MZold')
        self.record={**ports.clean({'repository':broken_bond.ORIGINAL,'folderName':'old-broken','name':'Broken Bond'}),'configured':True,'executable':'broken_bond_launcher.exe','runtime':'proton','tag':'v0.1.0-beta'}
        atomic_json(self.folder/'.deck-library-port.json',self.record);atomic_json(self.store.root/'ports.json',{broken_bond.ORIGINAL:self.record})
        self.entry=Entry('Broken Bond',['/bin/true'],source=str(self.folder/'broken_bond_launcher.exe'),id=ports.port_id(broken_bond.ORIGINAL),cover='/tmp/chosen-cover.png',metadata={'port_repository':broken_bond.ORIGINAL,'steam_appid':123,'steam_account':'/tmp/fake-steam','proton_version':'Proton 9.0 (Beta)'})
        self.other=Entry('Other',['/bin/false']);self.store.save([self.entry,self.other]);data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive:
            archive.writestr('Naruto The Broken Bond PC.exe',b'MZnew');archive.writestr('naruto.toml','user_language = 5\ncustom_option = "keep"\nmsaa_samples = 2\n')
        self.payload=data.getvalue();self.release={'tag_name':'v2.5','assets':[{'name':'BrokenBond-win64.zip','browser_download_url':'https://github.com/owner/repo/game.zip'}]}
        for p in (patch.object(proton_tools,'resolve',return_value=self.root/'proton'),patch.object(port_removal,'in_use',return_value=False),patch.object(ports,'download',side_effect=lambda url,path,**kwargs:path.write_bytes(self.payload))):
            p.start();self.addCleanup(p.stop)
    def repair(self,entry=None):return broken_bond.repair(entry or self.entry,self.store,self.ports,progress=lambda *_:None,get=lambda _:self.release)
    def test_migration_preserves_saves_steam_identity_artwork_and_originals_without_duplicates(self):
        result=self.repair();entry=result['entry'];new=pathlib.Path(entry.source).parent
        self.assertEqual(entry.id,self.entry.id);self.assertEqual(entry.cover,self.entry.cover);self.assertEqual(entry.metadata['steam_appid'],123);self.assertEqual(entry.metadata['proton_version'],'Proton 11.0');self.assertEqual(entry.metadata['port_repository'],broken_bond.COMPATIBLE)
        self.assertEqual((new/'hdd/save.dat').read_text(),'progress');self.assertTrue((new/'game/default.xex').is_file());self.assertTrue(pathlib.Path(result['backup']).is_dir());self.assertFalse(self.folder.exists());self.assertEqual(len(self.store.load()),2)
        self.assertNotIn(broken_bond.ORIGINAL,ports.records(self.store));self.assertEqual(broken_bond.status(entry,self.store),'applied')
        values=tomllib.loads((new/'naruto.toml').read_text());self.assertEqual(values['user_language'],5);self.assertEqual(values['custom_option'],'keep');self.assertEqual(values['msaa_samples'],1);self.assertFalse(values['mnk_mode'])
        self.store.merge(ports.entries_for(new),overwrite=False);self.assertEqual(len(self.store.load()),2);self.assertEqual(ports.entry_for(new).id,self.entry.id)
    def test_failed_promotion_rolls_back_original_files_and_library(self):
        rename=pathlib.Path.rename
        def fail(source,target):
            if source.parent.name=='packages' and pathlib.Path(target).parent==self.ports:raise OSError('Simulated promotion failure')
            return rename(source,target)
        with patch.object(pathlib.Path,'rename',fail),self.assertRaises(OSError):self.repair()
        self.assertTrue((self.folder/'game/default.xex').is_file());self.assertEqual((self.folder/'user/save.dat').read_text(),'progress');self.assertEqual(self.store.load(),[self.entry,self.other]);self.assertIn(broken_bond.ORIGINAL,ports.records(self.store))
    def test_running_games_wrong_ownership_and_external_game_symlinks_are_not_moved(self):
        with patch.object(port_removal,'in_use',return_value=True),self.assertRaises(ValueError):self.repair()
        (self.folder/'game').rename(self.root/'external');(self.folder/'game').symlink_to(self.root/'external',target_is_directory=True)
        with self.assertRaises(ValueError):self.repair()
        self.assertTrue((self.root/'external/default.xex').is_file())
    def test_compatible_port_update_preserves_legacy_id_game_data_and_shader_guard(self):
        first=self.repair();entry=first['entry'];folder=pathlib.Path(entry.source).parent;record=ports.records(self.store)[broken_bond.COMPATIBLE];record['tag']='v2.0'
        atomic_json(folder/'.deck-library-port.json',record);atomic_json(self.store.root/'ports.json',{broken_bond.COMPATIBLE:record});(folder/'pipeline-guard.txt').write_text('known shader');(folder/'pipeline-guard-pending.txt').write_text('pending shader')
        self.release['tag_name']='v2.6';result=self.repair(entry)
        self.assertEqual(result['entry'].id,self.entry.id);self.assertEqual(result['entry'].metadata['port_tag'],'v2.6');self.assertTrue(result['entry'].metadata['configured']);self.assertEqual((folder/'pipeline-guard.txt').read_text(),'known shader');self.assertEqual((folder/'hdd/save.dat').read_text(),'progress');self.assertTrue((folder/'game/default.xex').is_file())
        self.assertEqual((folder/'pipeline-guard-pending.txt').read_text(),'pending shader')
    def test_post_install_defaults_keep_custom_settings_on_later_configuration(self):
        folder=self.root/'new';folder.mkdir();config=folder/'naruto.toml';config.write_text('user_language = 5\nmsaa_samples = 2\n');record={'repository':broken_bond.COMPATIBLE}
        broken_bond.defaults(folder,record);self.assertEqual(tomllib.loads(config.read_text())['msaa_samples'],1)
        config.write_text(config.read_text().replace('msaa_samples = 1','msaa_samples = 4'));broken_bond.defaults(folder,record);self.assertEqual(tomllib.loads(config.read_text())['msaa_samples'],4);self.assertEqual(tomllib.loads(config.read_text())['user_language'],5)
        self.assertEqual(len(list((folder/'.deck-library-settings-backups').glob('*/naruto.toml'))),1)
    def test_extracted_originals_can_be_prepared_for_the_compatible_port_without_an_iso(self):
        spec=ports.clean({'repository':broken_bond.COMPATIBLE})['original_data'];target=self.root/'new';target.mkdir()
        original_data.prepare(target,self.folder/'game',spec,progress=lambda *_:None)
        self.assertTrue((target/'game/default.xex').is_file());self.assertFalse((target/'assets').exists())

    def test_fresh_install_configuration_applies_the_steam_deck_defaults_automatically(self):
        item=ports.clean({'repository':broken_bond.COMPATIBLE})
        ports.install(item,self.store,self.ports,get=lambda _:self.release,progress=lambda *_:None,runtime='proton')
        ports.set_input(broken_bond.COMPATIBLE,'original_data',str(self.folder/'game'),self.store)
        configured=ports.configure(broken_bond.COMPATIBLE,self.store,progress=lambda *_:None,home=self.root)
        self.assertTrue(configured['configured']);self.assertEqual(configured['steam_deck_fix']['id'],broken_bond.FIX)
        target=self.ports/item['folder'];values=tomllib.loads((target/'naruto.toml').read_text())
        self.assertEqual(values['internal_resolution_scale'],1.0);self.assertEqual(values['msaa_samples'],1);self.assertTrue((target/'game/default.xex').is_file())

    def test_migrated_raw_folder_launch_has_an_explicit_windows_game_root_and_the_new_runtime(self):
        result=self.repair();folder=pathlib.Path(result['entry'].source).parent
        with patch.object(project2099,'proton_env',return_value={}):command,env=port_runtime.command_for(folder,self.store,preferred='Proton 11.0')
        self.assertIn('--game_data_root=Z:'+str(folder/'game').replace('/','\\'),command)
        self.assertEqual(env['STEAM_COMPAT_DATA_PATH'],str(self.store.root/'runtimes/ports'/ports.port_id(broken_bond.COMPATIBLE)))


class ShaderRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.folder=pathlib.Path(self.temp.name)
        atomic_json(self.folder/'.deck-library-port.json',{'repository':broken_bond.COMPATIBLE})
        self.command=['proton','run',str(self.folder/'game.exe')];self.pending=self.folder/'pipeline-guard-pending.txt'
    def key(self,n):return f'vs={n:016x} ps=0000000000000001 w=00000001'
    def test_a_new_shader_failure_retries_and_then_returns_the_success_code(self):
        def call(*_,**__):self.pending.write_text(self.key(1));return 3 if launch.call_count==1 else 0
        with patch.object(port_runtime.subprocess,'call',side_effect=call) as launch,patch.object(port_runtime.time,'sleep'):
            self.assertEqual(port_runtime.run(self.command,{},self.folder),0);self.assertEqual(launch.call_count,2)
    def test_repeated_shaders_and_unrelated_exit_codes_are_not_retried(self):
        for code in (3,2):
            self.pending.write_text(self.key(1))
            with patch.object(port_runtime.subprocess,'call',return_value=code) as launch,patch.object(port_runtime.time,'sleep'):
                self.assertEqual(port_runtime.run(self.command,{},self.folder),code);launch.assert_called_once()
    def test_recovery_is_bounded_even_if_each_launch_identifies_a_new_shader(self):
        def call(*_,**__):self.pending.write_text(self.key(launch.call_count));return 3
        with patch.object(port_runtime.subprocess,'call',side_effect=call) as launch,patch.object(port_runtime.time,'sleep'):
            self.assertEqual(port_runtime.run(self.command,{},self.folder),3);self.assertEqual(launch.call_count,7)
    def test_malformed_pending_records_and_other_ports_do_not_trigger_recovery(self):
        def call(*_,**__):self.pending.write_text('unrelated error');return 3
        with patch.object(port_runtime.subprocess,'call',side_effect=call) as launch:
            self.assertEqual(port_runtime.run(self.command,{},self.folder),3);launch.assert_called_once()
        atomic_json(self.folder/'.deck-library-port.json',{'repository':'other/port'})
        def other(*_,**__):self.pending.write_text(self.key(1));return 3
        with patch.object(port_runtime.subprocess,'call',side_effect=other) as launch:
            self.assertEqual(port_runtime.run(self.command,{},self.folder),3);launch.assert_called_once()

if __name__=='__main__':unittest.main()
