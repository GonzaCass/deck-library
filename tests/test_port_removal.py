import json,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import port_removal,ports,service,updates
from deck_library.models import Store,Entry,atomic_json


class PortRemovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'private');self.ports=self.root/'ports';self.folder=self.ports/'game'
        self.repo='owner/game';self.record={'repository':self.repo,'folder':'game','name':'Test game','executable':'game.exe','runtime':'proton'}
        self.make_copy(self.folder);atomic_json(self.store.root/'ports.json',{self.repo:self.record})
        self.entry=Entry('Test game',['/bin/true'],source=str(self.folder/'game.exe'),id=ports.port_id(self.repo),metadata={'port_repository':self.repo});self.other=Entry('Another game',['/bin/false'])
        self.store.save([self.entry,self.other]);self.prefix=self.store.root/'runtimes/ports'/self.entry.id;self.prefix.mkdir(parents=True);(self.prefix/'save.dat').write_text('save')
    def make_copy(self,folder,repository=None):
        folder.mkdir(parents=True);atomic_json(folder/'.deck-library-port.json',{**self.record,'repository':repository or self.repo});(folder/'game.exe').write_bytes(b'MZ');(folder/'save.dat').write_text('save')
    def execute(self,**kwargs):return port_removal.execute(self.repo,self.store,self.ports,**kwargs)
    def test_complete_removal_cleans_owned_copies_runtime_and_metadata_but_preserves_external_originals(self):
        old=self.ports/'.deck-library-replaced/game-old';removed=self.ports/ports.REMOVED/'game-removed';other=self.ports/'.deck-library-replaced/unrelated'
        for p in (old,removed):self.make_copy(p)
        self.make_copy(other,'another/port');original=self.root/'original.iso';original.write_text('original');(self.prefix/'z-drive').symlink_to(self.root,target_is_directory=True)
        for name in ('applied-presets','preferred-presets','logs','launchers'):
            directory=self.store.root/name;directory.mkdir();(directory/(self.entry.id+('.sh' if name=='launchers' else '.log' if name=='logs' else '.json'))).write_text('data')
        backups=self.store.root/'preset-backups'/self.entry.id;backups.mkdir(parents=True);(backups/'original').write_text('config')
        atomic_json(updates.cache_path(self.store),{'catalog':[{'repository':self.repo},{'repository':'another/port'}]})
        self.execute()
        for path in (self.folder,old,removed,self.prefix,backups):self.assertFalse(path.exists(),path)
        self.assertEqual(original.read_text(),'original');self.assertTrue(other.is_dir());self.assertEqual(self.store.load(),[self.other]);self.assertNotIn(self.repo,ports.records(self.store));self.assertEqual(updates.cached(self.store)['catalog'],[{'repository':'another/port'}])
    def test_untrusted_receipt_shared_folder_and_symbolic_paths_are_refused_before_deletion(self):
        atomic_json(self.folder/'.deck-library-port.json',{'repository':'different/owner'})
        with self.assertRaises(ValueError):self.execute()
        atomic_json(self.folder/'.deck-library-port.json',self.record);atomic_json(self.store.root/'ports.json',{self.repo:self.record,'other/port':{**self.record,'repository':'other/port'}})
        with self.assertRaises(ValueError):self.execute()
        atomic_json(self.store.root/'ports.json',{self.repo:self.record});self.folder.rename(self.ports/'elsewhere');self.folder.symlink_to(self.ports/'elsewhere',target_is_directory=True)
        with self.assertRaises(ValueError):self.execute()
        self.assertTrue((self.ports/'elsewhere/save.dat').is_file());self.assertTrue(self.prefix.is_dir())
    def test_a_symlinked_runtime_parent_cannot_delete_external_data(self):
        self.prefix.rename(self.root/'external-prefix');(self.store.root/'runtimes/ports').rmdir();(self.store.root/'runtimes/ports').symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):self.execute()
        self.assertTrue(self.folder.is_dir());self.assertTrue((self.root/'external-prefix/save.dat').is_file())
    def test_running_game_or_a_changed_installation_is_not_deleted(self):
        expected=port_removal.plan(self.repo,self.store,self.ports)
        with patch.object(port_removal,'in_use',return_value=True),self.assertRaises(ValueError):self.execute()
        self.folder.rename(self.ports/'moved');self.make_copy(self.folder)
        with self.assertRaises(ValueError):self.execute(expected=expected)
        self.assertTrue(self.folder.is_dir());self.assertIn(self.repo,ports.records(self.store))
    def test_steam_removal_is_queued_before_forgetting_entries_and_keeps_unrelated_pending_work(self):
        self.entry.metadata.update(steam_account=str(self.root/'steam'),steam_appid=77);self.store.save([self.entry,self.other])
        atomic_json(self.store.root/'pending.json',{'account':str(self.root/'steam'),'ids':[self.entry.id,self.other.id],'art':[{'appid':77,'slot':'icon','file':'a'},{'appid':99,'slot':'icon','file':'b'}],'controllers':[77,99]})
        def queue(ids,account,store,**kwargs):
            self.assertIn(self.entry,store.load());self.assertEqual(ids,[77]);self.assertEqual(account,self.root/'steam');return {'state':'pending','count':1}
        with patch.object(service,'queue_removals',side_effect=queue) as queued:result=self.execute(start_worker=False)
        self.assertEqual(result['steam']['state'],'pending');queued.assert_called_once();pending=json.loads((self.store.root/'pending.json').read_text());self.assertEqual(pending['ids'],[self.other.id]);self.assertEqual(pending['controllers'],[99]);self.assertEqual([p['appid'] for p in pending['art']],[99])
    def test_steam_queue_failure_does_not_delete_game_files(self):
        self.entry.metadata.update(steam_account=str(self.root/'steam'),steam_appid=77);self.store.save([self.entry,self.other])
        with patch.object(service,'queue_removals',side_effect=ValueError('Queue unavailable')),self.assertRaises(ValueError):self.execute()
        self.assertTrue(self.folder.is_dir());self.assertTrue(self.prefix.is_dir());self.assertIn(self.entry,self.store.load())
    def test_process_detection_handles_native_cwd_and_wine_paths_without_matching_text_mentions(self):
        proc=self.root/'proc';process=proc/'123';process.mkdir(parents=True)
        (process/'cmdline').write_text('python\0a message about '+str(self.folder)+'\0');self.assertFalse(port_removal.in_use([self.folder],proc))
        (process/'cmdline').write_text('Z:'+str(self.folder/'game.exe').replace('/','\\')+'\0');self.assertTrue(port_removal.in_use([self.folder],proc))
        (process/'cmdline').write_text('game\0');(process/'cwd').symlink_to(self.folder,target_is_directory=True);self.assertTrue(port_removal.in_use([self.folder],proc))

if __name__=='__main__':unittest.main()
