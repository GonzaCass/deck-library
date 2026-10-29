import pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import game_removal,ports,port_removal,service
from deck_library.models import Store,Entry,atomic_json
from deck_library.installations import settings,save_settings


class GameRemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'private')
        self.folder=self.root/'ports/game';self.folder.mkdir(parents=True)
        self.exe=self.folder/'game.exe';self.exe.write_bytes(b'fixture')
        (self.folder/'save.dat').write_text('save')
        self.entry=Entry('Game',[str(self.exe)],source=str(self.exe),cwd=str(self.folder))
        self.store.save([self.entry]);save_settings({'port_roots':[str(self.folder.parent)]},self.store)

    def test_library_only_survives_discovery_without_deleting_files_or_breaking_launchers(self):
        self.entry.metadata.update(steam_appid=123,steam_account='account');self.store.save([self.entry])
        game_removal.set_hidden(self.entry.id,True,self.store)
        self.store.merge([self.entry])
        self.assertEqual(game_removal.library_entries(self.store.load(),settings(self.store))[0],[])
        self.assertEqual(self.store.load(),[self.entry]);self.assertTrue(self.exe.exists())
        self.assertFalse((self.store.root/'pending.json').exists())
        game_removal.set_hidden(self.entry.id,False,self.store)
        self.assertEqual(game_removal.library_entries(self.store.load(),settings(self.store))[0],[self.entry])

    def test_hiding_a_port_keeps_its_rom_associated_but_emulator_filter_can_show_it(self):
        rom=Entry('Game',['dolphin','/tmp/game.iso'],kind='emulated',platform='Wii',source='/tmp/game.iso')
        self.entry.metadata['original_platform']='Wii';self.store.save([self.entry,rom])
        game_removal.set_hidden(self.entry.id,True,self.store)
        self.assertEqual(game_removal.library_entries(self.store.load(),settings(self.store))[0],[])
        self.assertEqual(game_removal.library_entries(self.store.load(),settings(self.store),False)[0],[rom])

    def test_full_port_removal_deletes_only_its_directory_and_private_data(self):
        external=self.root/'original.iso';external.write_text('original')
        (self.folder/'external').symlink_to(external)
        runtime=self.store.root/'runtimes/ports'/self.entry.id;runtime.mkdir(parents=True);(runtime/'save').write_text('save')
        with patch.object(port_removal,'in_use',return_value=False):
            value=game_removal.plan(self.entry,self.store)
            game_removal.execute(self.entry,self.store,expected=value,start_worker=False)
        self.assertFalse(self.folder.exists());self.assertFalse(runtime.exists());self.assertTrue(external.exists());self.assertEqual(self.store.load(),[])

    def test_unknown_directory_shared_directory_and_symlink_are_never_deleted(self):
        save_settings({'port_roots':[]},self.store)
        with self.assertRaises(ValueError):game_removal.plan(self.entry,self.store)
        save_settings({'port_roots':[str(self.folder.parent)]},self.store)
        other=Entry('Other',['/bin/true'],source=str(self.folder/'save.dat'))
        self.store.save([self.entry,other])
        with self.assertRaises(ValueError):game_removal.plan(self.entry,self.store)
        self.store.save([self.entry]);self.folder.rename(self.root/'elsewhere');self.folder.symlink_to(self.root/'elsewhere',target_is_directory=True)
        with self.assertRaises(ValueError):game_removal.plan(self.entry,self.store)
        self.assertTrue((self.root/'elsewhere/save.dat').exists())

    def test_changed_installation_and_running_game_are_preserved(self):
        value=game_removal.plan(self.entry,self.store)
        with patch.object(port_removal,'in_use',return_value=True),self.assertRaises(ValueError):game_removal.execute(self.entry,self.store,expected=value)
        self.folder.rename(self.root/'old');self.folder.mkdir();self.exe.write_bytes(b'new')
        with self.assertRaises(ValueError):game_removal.execute(self.entry,self.store,expected=value)
        self.assertTrue(self.exe.exists())

    def test_rom_removal_preserves_shared_emulator_saves_and_other_games(self):
        rom=self.root/'game.iso';rom.write_bytes(b'rom');saves=self.root/'emulator/saves';saves.mkdir(parents=True);(saves/'shared.dat').write_text('save')
        entry=Entry('ROM',['dolphin',str(rom)],kind='emulated',source=str(rom));self.store.save([entry,self.entry])
        with patch.object(port_removal,'in_use',return_value=False):game_removal.execute(entry,self.store,start_worker=False)
        self.assertFalse(rom.exists());self.assertTrue((saves/'shared.dat').exists());self.assertEqual(self.store.load(),[self.entry])

    def test_shared_cue_tracks_and_playlists_are_not_deleted(self):
        track=self.root/'disc.bin';track.write_bytes(b'track');cue=self.root/'disc.cue';cue.write_text('FILE "disc.bin" BINARY\n')
        entry=Entry('Disc',['duckstation',str(cue)],kind='emulated',source=str(cue));other_cue=self.root/'other.cue';other_cue.write_text(cue.read_text())
        other=Entry('Other',['duckstation',str(other_cue)],kind='emulated',source=str(other_cue));self.store.save([entry,other])
        with self.assertRaises(ValueError):game_removal.plan(entry,self.store)
        playlist=self.root/'discs.m3u';playlist.write_text('disc.cue\n');entry=Entry('Set',['duckstation',str(playlist)],kind='emulated',source=str(playlist))
        with self.assertRaises(ValueError):game_removal.plan(entry,self.store)
        self.assertTrue(track.exists())

    def test_prism_only_removes_the_verified_instance(self):
        folder=self.root/'prism/instances/a';folder.mkdir(parents=True);cfg=folder/'instance.cfg';cfg.write_text('[General]')
        other=folder.parent/'b';other.mkdir();(other/'world.dat').write_text('world')
        entry=Entry('Minecraft',['prism','--launch','a'],kind='minecraft',source=str(cfg),metadata={'instance_root':str(folder)})
        self.store.save([entry])
        with patch('deck_library.discovery.prism_installations',return_value=[{'instances':str(folder.parent)}]),patch.object(port_removal,'in_use',return_value=False):
            game_removal.execute(entry,self.store,start_worker=False)
        self.assertFalse(folder.exists());self.assertTrue((other/'world.dat').exists())

    def test_failed_steam_queue_preserves_files_and_entry(self):
        self.entry.metadata.update(steam_appid=123,steam_account=str(self.root/'steam'));self.store.save([self.entry])
        with patch.object(port_removal,'in_use',return_value=False),patch.object(service,'queue_removals',side_effect=ValueError('offline')),self.assertRaises(ValueError):game_removal.execute(self.entry,self.store)
        self.assertTrue(self.exe.exists());self.assertEqual(self.store.load(),[self.entry])

    def test_changed_library_target_is_revalidated_before_deletion(self):
        expected=game_removal.plan(self.entry,self.store)
        folder=self.folder.parent/'new';folder.mkdir();exe=folder/'new.exe';exe.write_text('new')
        replacement=Entry('Game',[str(exe)],source=str(exe),id=self.entry.id);self.store.save([replacement])
        with self.assertRaises(ValueError):game_removal.execute(self.entry,self.store,expected=expected)
        self.assertTrue(self.exe.exists());self.assertTrue(exe.exists());self.assertEqual(self.store.load(),[replacement])

    def test_managed_port_still_uses_its_receipt_and_owned_runtime(self):
        repo='test/game';record={'repository':repo,'name':'Game','folder':'game'}
        atomic_json(self.folder/'.deck-library-port.json',record);atomic_json(self.store.root/'ports.json',{repo:record})
        self.entry.metadata['port_repository']=repo;self.store.save([self.entry])
        with patch.object(ports,'ports_root',return_value=self.folder.parent),patch.object(port_removal,'in_use',return_value=False):
            value=game_removal.plan(self.entry,self.store);self.assertTrue(value['managed'])
            game_removal.execute(self.entry,self.store,expected=value,start_worker=False)
        self.assertFalse(self.folder.exists());self.assertEqual(ports.records(self.store),{})

    def test_managed_receipt_does_not_allow_deleting_another_games_files(self):
        repo='test/game';record={'repository':repo,'name':'Game','folder':'game'}
        atomic_json(self.folder/'.deck-library-port.json',record);atomic_json(self.store.root/'ports.json',{repo:record})
        self.entry.metadata['port_repository']=repo
        other=Entry('Other',['/bin/true'],source=str(self.folder/'save.dat'));self.store.save([self.entry,other])
        with patch.object(ports,'ports_root',return_value=self.folder.parent),self.assertRaises(ValueError):game_removal.plan(self.entry,self.store)
        self.assertTrue(self.exe.exists());self.assertTrue((self.folder/'save.dat').exists())
