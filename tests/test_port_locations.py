import json,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import ports,port_locations as locations,port_runtime,switch_port,runtime,discovery,port_removal
from deck_library.models import Store,Entry,atomic_json


class PortLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=pathlib.Path(self.temp.name);self.store=Store(self.home/'.local/share/deck-library')
        self.root=self.home/'ports';self.root.mkdir()
        self.repo='owner/Portable';self.folder=self.root/'Portable'
        self.record={'repository':self.repo,'name':'Portable','folder':'Portable','executable':'game.AppImage','runtime':'linux','tag':'v1','configured':True}
        self.make_port(self.folder)
        atomic_json(self.store.root/'ports.json',{self.repo:self.record})
        self.entry=ports.entry_for(self.folder);self.entry.cover='my-cover.png';self.entry.metadata.update(steam_appid=1234,steam_account='/private/account',proton_version='GE-Proton')
        self.store.save([self.entry])
    def make_port(self,folder,record=None):
        value=record or self.record;folder.mkdir(parents=True,exist_ok=True)
        binary=folder/value['executable'];binary.parent.mkdir(parents=True,exist_ok=True);binary.write_bytes(b'\x7fELFfixture');binary.chmod(0o755)
        atomic_json(folder/'.deck-library-port.json',value)
    def test_moved_receipt_is_found_in_ports_and_keeps_identity_steam_art_and_runtime(self):
        moved=self.root/'Moved game';self.folder.rename(moved)
        fresh=locations.recover(self.entry,self.store,self.home)
        self.assertEqual(fresh.id,self.entry.id);self.assertEqual(fresh.metadata['steam_appid'],1234);self.assertEqual(fresh.cover,'my-cover.png')
        self.assertEqual(fresh.metadata['proton_version'],'GE-Proton');self.assertEqual(fresh.source,str(moved/'game.AppImage'))
        self.assertEqual(ports.folder_for(ports.records(self.store)[self.repo]),moved)
        self.assertFalse((self.store.root/'pending.json').exists())
        self.assertEqual(json.loads((moved/'.deck-library-port.json').read_text()),self.record)
    def test_multiple_candidates_require_a_choice_and_unrelated_receipts_are_not_candidates(self):
        self.folder.rename(self.root/'First');self.make_port(self.root/'Second')
        self.make_port(self.root/'Other',{**self.record,'repository':'other/port'})
        self.assertEqual(len(locations.candidates(self.repo,self.store,self.home)),2)
        self.assertIs(locations.recover(self.entry,self.store,self.home),self.entry)
        self.assertEqual(self.store.load()[0].source,self.entry.source)
    def test_missing_card_does_not_forget_anything_or_create_a_new_directory(self):
        moved=self.home/'card/Games/Portable';self.folder.rename(self.root/'temp')
        record={**self.record,'install_path':str(moved)};atomic_json(self.store.root/'ports.json',{self.repo:record})
        before=self.store.path.read_bytes()
        self.assertIn('microSD',locations.problem(self.entry,self.store));self.assertFalse(moved.exists())
        self.assertEqual(self.store.path.read_bytes(),before)
    def test_selected_external_directory_with_spaces_works_without_a_receipt(self):
        folder=self.home/'Tarjeta SD/Juegos/Port ajeno';folder.mkdir(parents=True)
        exe=folder/'game.AppImage';exe.write_bytes(b'\x7fELFfixture');exe.chmod(0o755)
        fresh=locations.link(self.repo,folder,self.store,entry=self.entry,home=self.home)
        record=ports.records(self.store)[self.repo]
        self.assertTrue(record['external_install']);self.assertEqual(record['tag'],'')
        self.assertEqual(fresh.id,self.entry.id);self.assertEqual(fresh.source,str(exe))
        self.assertFalse((folder/'.deck-library-port.json').exists())
        with self.assertRaisesRegex(ValueError,'vinculada'):port_removal.plan(self.repo,self.store,self.root)
        with patch.object(ports,'fetch_json') as fetch:self.assertEqual(ports.installed_updates(self.store,get=fetch),[]);fetch.assert_not_called()
    def test_wrong_game_invalid_path_and_ambiguous_executables_leave_store_untouched(self):
        before=self.store.path.read_bytes();registry=(self.store.root/'ports.json').read_bytes()
        other=self.home/'Wrong';self.make_port(other,{**self.record,'repository':'someone/else'})
        with self.assertRaisesRegex(ValueError,'otro port'):locations.link(self.repo,other,self.store,home=self.home)
        ambiguous=self.home/'Ambiguous';ambiguous.mkdir()
        for name in ('one.exe','two.exe'):(ambiguous/name).write_bytes(b'MZfixture')
        with self.assertRaisesRegex(ValueError,'ejecutable'):locations.link(self.repo,ambiguous,self.store,home=self.home)
        with self.assertRaisesRegex(ValueError,'principal'):locations.link(self.repo,self.home,self.store,home=self.home)
        self.assertEqual(self.store.path.read_bytes(),before);self.assertEqual((self.store.root/'ports.json').read_bytes(),registry)
    def test_manual_port_without_a_repository_can_be_relocated(self):
        manual=Entry('Manual',[str(self.folder/'game.AppImage'),'--play'],source=str(self.folder/'game.AppImage'),cwd=str(self.folder))
        self.store.save([manual]);target=self.home/'Elsewhere';self.folder.rename(target)
        fresh=locations.link_entry(manual,target,self.store)
        self.assertEqual(fresh.id,manual.id);self.assertEqual(fresh.command,[str(target/'game.AppImage'),'--play']);self.assertEqual(fresh.cwd,str(target))
    def test_manual_ports_offer_filename_matches_in_ports_without_selecting_one_automatically(self):
        manual=Entry('Manual',[str(self.folder/'game.AppImage')],source=str(self.folder/'game.AppImage'))
        self.store.save([manual]);target=self.root/'Moved';self.folder.rename(target)
        self.assertEqual(locations.manual_candidates(manual,self.store,self.home),[target])
        self.assertIs(locations.recover(manual,self.store,self.home),manual)
    def test_windows_external_install_keeps_a_private_prefix_and_selected_runtime(self):
        folder=self.home/'External Windows';folder.mkdir();(folder/'game.exe').write_bytes(b'MZfixture')
        fresh=locations.link(self.repo,folder,self.store,entry=self.entry,home=self.home,executable=folder/'game.exe')
        self.assertEqual(fresh.platform,'Windows')
        with patch('deck_library.proton_tools.resolve',return_value=self.home/'proton'),patch.object(port_runtime.project2099,'proton_env',return_value={}):
            command,env=port_runtime.command_for(folder,self.store,preferred='GE-Proton')
        self.assertEqual(command[2],str(folder/'game.exe'));self.assertEqual(env['STEAM_COMPAT_DATA_PATH'],str(self.store.root/'runtimes/ports'/self.entry.id))
    def test_discovery_keeps_a_registered_external_install_without_scanning_its_parent(self):
        target=self.home/'Card/Outside';target.parent.mkdir();self.folder.rename(target)
        fresh=locations.link(self.repo,target,self.store,home=self.home,entry=self.entry)
        scanned=discovery.scan(self.home,preferences={})
        matching=[e for e in scanned if e.id==fresh.id]
        self.assertEqual(len(matching),1);self.assertEqual(matching[0].source,fresh.source)
    def test_originals_inside_the_moved_installation_follow_it(self):
        data=self.folder/'originals';data.mkdir();record={**self.record,'inputs':{'original_data':str(data)}}
        atomic_json(self.folder/'.deck-library-port.json',record);atomic_json(self.store.root/'ports.json',{self.repo:record})
        target=self.home/'Moved';self.folder.rename(target)
        locations.link(self.repo,target,self.store,home=self.home,entry=self.entry)
        self.assertEqual(ports.records(self.store)[self.repo]['inputs']['original_data'],str(target/'originals'))
    def test_latest_original_selection_survives_an_older_receipt(self):
        selected=self.folder/'new-originals';selected.mkdir()
        atomic_json(self.store.root/'ports.json',{self.repo:{**self.record,'inputs':{'original_data':str(selected)}}})
        target=self.home/'Moved';self.folder.rename(target)
        locations.link(self.repo,target,self.store,home=self.home,entry=self.entry)
        self.assertEqual(ports.records(self.store)[self.repo]['inputs']['original_data'],str(target/'new-originals'))
    def test_custom_launch_arguments_remain_when_the_port_is_moved(self):
        self.entry.command.append('--custom-setting');self.entry.metadata['manual_command']=True;self.store.save([self.entry])
        target=self.home/'Moved';self.folder.rename(target)
        fresh=locations.link(self.repo,target,self.store,home=self.home,entry=self.entry)
        self.assertEqual(fresh.command,[str(target/'game.AppImage'),'--custom-setting']);self.assertTrue(fresh.metadata['manual_command'])
    def test_updates_use_the_relocated_folder_and_keep_a_backup_and_saves(self):
        target=self.home/'SD Card/Custom name';target.parent.mkdir();self.folder.rename(target)
        (target/'saves').mkdir();(target/'saves/progress').write_bytes(b'save')
        fresh=locations.link(self.repo,target,self.store,home=self.home,entry=self.entry)
        release={'tag_name':'v2','assets':[{'name':'game-linux-x86_64.AppImage','browser_download_url':'https://example.org/game'}]}
        with patch.object(ports,'download',side_effect=lambda url,path,**_:path.write_bytes(b'\x7fELFupdated')):
            result=ports.install(ports.clean(self.record),self.store,self.root,replace=True,get=lambda _:release,progress=lambda _:None)
        self.assertEqual(result['install_path'],str(target));self.assertEqual((target/'saves/progress').read_bytes(),b'save')
        self.assertEqual((target/result['executable']).read_bytes(),b'\x7fELFupdated')
        self.assertTrue(list((target.parent/'.deck-library-replaced').iterdir()))
        self.assertEqual(ports.entry_for(target).id,fresh.id)
    def test_reinstalling_a_linked_external_port_creates_a_managed_copy_and_keeps_the_original(self):
        external=self.home/'Someone elses/Game';external.mkdir(parents=True);exe=external/'game.AppImage';exe.write_bytes(b'old');exe.chmod(0o755)
        locations.link(self.repo,external,self.store,home=self.home,entry=self.entry)
        # This fixture also has an old managed copy: it must not be overwritten.
        release={'tag_name':'v2','assets':[{'name':'game-linux-x86_64.AppImage','browser_download_url':'https://example.org/game'}]}
        with self.assertRaisesRegex(ValueError,'destino'):ports.install(ports.clean(self.record),self.store,self.root,replace=True,get=lambda _:release)
        self.folder.rename(self.root/'Old copy')
        with patch.object(ports,'download',side_effect=lambda url,path,**_:path.write_bytes(b'\x7fELFnew')):
            result=ports.install(ports.clean(self.record),self.store,self.root,replace=True,get=lambda _:release,progress=lambda _:None)
        self.assertEqual(exe.read_bytes(),b'old');self.assertEqual(result['install_path'],str(self.folder));self.assertFalse(result.get('external_install'))
    def test_a_multi_game_bundle_keeps_both_steam_ids_after_relocation(self):
        record={**self.record,'games':[{'executable':'game.AppImage','title':'First'},{'executable':'second.AppImage','title':'Second'}]}
        self.make_port(self.folder,{**record,'executable':'second.AppImage'})
        atomic_json(self.folder/'.deck-library-port.json',record);atomic_json(self.store.root/'ports.json',{self.repo:record})
        entries=ports.entries_for(self.folder)
        for number,e in enumerate(entries):e.metadata['steam_appid']=2000+number
        self.store.save(entries);target=self.home/'Moved';self.folder.rename(target)
        locations.link(self.repo,target,self.store,home=self.home,entry=entries[0])
        after=self.store.load();self.assertEqual({e.id for e in after},{e.id for e in entries});self.assertEqual({e.metadata['steam_appid'] for e in after},{2000,2001})
        self.assertTrue(all(pathlib.Path(e.source).is_relative_to(target) for e in after))
    def test_missing_external_media_requires_an_explicit_reinstall_before_using_the_default_folder(self):
        record={**self.record,'install_path':str(self.home/'Disconnected Card/Game'),'entry_id':self.entry.id}
        atomic_json(self.store.root/'ports.json',{self.repo:record});self.folder.rename(self.root/'Old copy')
        release={'tag_name':'v2','assets':[{'name':'game-linux-x86_64.AppImage','browser_download_url':'https://example.org/game'}]}
        with self.assertRaisesRegex(ValueError,'microSD'):ports.install(ports.clean(self.record),self.store,self.root,replace=True,get=lambda _:release)
        with patch.object(ports,'download',side_effect=lambda url,path,**_:path.write_bytes(b'\x7fELFnew')):
            result=ports.install(ports.clean(self.record),self.store,self.root,replace=True,reinstall_missing=True,get=lambda _:release,progress=lambda _:None)
        self.assertEqual(result['install_path'],str(self.folder));self.assertEqual(result['entry_id'],self.entry.id)
        self.assertFalse((self.home/'Disconnected Card').exists())
    def test_missing_switch_data_fails_cleanly_without_starting_a_process(self):
        repo=switch_port.REPOSITORY;record={**self.record,'repository':repo,'configured':True,'game_data_dir':str(self.home/'missing-data')}
        atomic_json(self.store.root/'ports.json',{repo:record});self.entry.metadata['port_repository']=repo
        with patch.object(runtime.subprocess,'Popen') as popen:
            self.assertEqual(runtime.launch(self.entry,self.store,notify=False),1);popen.assert_not_called()


class SavageDataLocationsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.home=pathlib.Path(self.temp.name);self.store=Store(self.home/'private')
        self.repo=switch_port.REPOSITORY;self.record={**ports.clean({'repository':self.repo}),'runtime':'linux','executable':'game.AppImage'}
        atomic_json(self.store.root/'ports.json',{self.repo:self.record})
        self.data=self.home/'SD Card/Already compiled'
        for name in ('exefs/main','romfs.bin','swgame.so'):
            file=self.data/'extracted'/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'fixture')
    def test_precompiled_game_outside_ports_does_not_require_originals_or_keys_again(self):
        switch_port.set_data(self.repo,self.data/'extracted',self.store)
        record=ports.records(self.store)[self.repo];self.assertTrue(switch_port.prepared(record,self.home,{}))
        self.assertTrue(all(ok for ok,_ in ports.requirements(record,[],self.home)))
        entry=Entry('Savage',['/bin/true'],metadata={'port_repository':self.repo})
        env=switch_port.launch_environment(entry,{},self.store,self.home)
        self.assertEqual(env['SAVAGEWIND_DATA_ROOT'],str(self.data));self.assertNotIn('SAVAGEWIND_LAUNCHER_SETUP',env)
        self.assertEqual((self.data/'extracted/romfs.bin').read_bytes(),b'fixture')
    def test_windows_game_requires_windows_module_and_uses_a_wine_path(self):
        record={**self.record,'runtime':'proton'};atomic_json(self.store.root/'ports.json',{self.repo:record})
        with self.assertRaisesRegex(ValueError,'módulo'):switch_port.set_data(self.repo,self.data,self.store)
        (self.data/'extracted/swgame.dll').write_bytes(b'MZfixture');switch_port.set_data(self.repo,self.data,self.store)
        entry=Entry('Savage',['/bin/true'],metadata={'port_repository':self.repo})
        env=switch_port.launch_environment(entry,{},self.store,self.home)
        self.assertEqual(env['SAVAGEWIND_DATA_ROOT'],'Z:'+str(self.data).replace('/','\\'))
    def test_a_lost_compiled_directory_does_not_fall_back_to_an_empty_default(self):
        switch_port.set_data(self.repo,self.data,self.store);self.data.rename(self.data.with_name('Moved'))
        entry=Entry('Savage',['/bin/true'],metadata={'port_repository':self.repo})
        with self.assertRaisesRegex(ValueError,'No se encuentran'):switch_port.launch_environment(entry,{},self.store,self.home)
