import pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import rom_locations,steam_inventory
from deck_library.models import Store,Entry,atomic_json


class RomLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'private')
        self.rom=self.root/'old/game.iso'
        self.entry=Entry('Game',['dolphin','-e',str(self.rom)],'emulated','Wii',str(self.rom),game_id='RMCE01',cover='custom.png',metadata={'preferred_profile':'quality'})
        self.store.save([self.entry])
    def test_missing_only_emulated_and_visible_and_recheck_sd(self):
        self.assertEqual(rom_locations.missing([self.entry]),[self.entry])
        self.assertFalse(rom_locations.missing([self.entry],{'hidden_entries':[self.entry.id]}))
        port=Entry('Port',['/abs/missing.AppImage'],source='/abs/missing.AppImage')
        self.assertEqual(rom_locations.missing([port]),[])
        self.rom.parent.mkdir();self.rom.write_bytes(b'rom')
        self.assertEqual(rom_locations.missing([self.entry]),[])
        with self.assertRaises(ValueError):rom_locations.forget(self.entry,self.store,start_worker=False)
        self.assertEqual(len(self.store.load()),1)
    def test_relocation_preserves_identity_profile_and_merges_unlinked_discovery(self):
        target=self.root/'moved/game.rvz';target.parent.mkdir();target.write_bytes(b'rom')
        duplicate=Entry('Game',['dolphin','-e',str(target)],'emulated','Wii',str(target))
        self.store.save([self.entry,duplicate])
        moved=rom_locations.relocate(self.entry,target,self.store,start_worker=False)
        self.assertEqual(moved.id,self.entry.id);self.assertEqual(moved.game_id,'RMCE01')
        self.assertEqual(moved.cover,'custom.png');self.assertEqual(moved.metadata,self.entry.metadata)
        self.assertEqual(moved.command,['dolphin','-e',str(target)])
        self.assertEqual(moved.cwd,str(target.parent));self.assertEqual(len(self.store.load()),1)
        self.assertEqual(target.read_bytes(),b'rom')
    def test_direct_steam_shortcut_queues_update_with_same_appid(self):
        target=self.root/'new.iso';target.write_bytes(b'rom');self.entry.metadata.update(steam_account=str(self.root/'account'),steam_appid=123)
        self.store.save([self.entry])
        with patch.object(steam_inventory,'shortcuts',return_value=[{'appid':123,'exe':'dolphin','options':str(self.rom)}]):
            fresh=rom_locations.relocate(self.entry,target,self.store,start_worker=False)
        import json
        pending=json.loads((self.store.root/'pending.json').read_text())
        self.assertEqual(pending['ids'],[self.entry.id]);self.assertEqual(fresh.metadata['steam_appid'],123)
        self.assertTrue((self.store.root/'launchers'/(self.entry.id+'.sh')).exists())
    def test_managed_steam_shortcut_needs_no_restart_to_relocate(self):
        target=self.root/'new.iso';target.write_bytes(b'rom');self.entry.metadata.update(steam_account=str(self.root/'account'),steam_appid=123);self.store.save([self.entry])
        with patch.object(steam_inventory,'shortcuts',return_value=[{'appid':123,'exe':str(self.store.root/'launchers'/(self.entry.id+'.sh')),'options':''}]):
            rom_locations.relocate(self.entry,target,self.store,start_worker=False)
        self.assertFalse((self.store.root/'pending.json').exists())
    def test_invalid_file_or_linked_duplicate_or_custom_command_write_nothing(self):
        target=self.root/'wrong.exe';target.write_bytes(b'MZ')
        before=self.store.path.read_bytes()
        with self.assertRaises(ValueError):rom_locations.relocate(self.entry,target,self.store)
        self.assertEqual(self.store.path.read_bytes(),before)
        target=self.root/'valid.iso';target.write_bytes(b'rom')
        duplicate=Entry('Duplicate',['dolphin',str(target)],'emulated','Wii',str(target),metadata={'steam_appid':345})
        self.store.save([self.entry,duplicate])
        with self.assertRaises(ValueError):rom_locations.relocate(self.entry,target,self.store)
        self.assertEqual(len(self.store.load()),2)
        self.entry.command=['custom','launch'];self.store.save([self.entry])
        with self.assertRaises(ValueError):rom_locations.relocate(self.entry,target,self.store)
    def test_switch_rejects_other_title_without_using_cached_identity(self):
        old=Entry('Game',['eden','/old.nsp'],'emulated','Switch','/old.nsp',game_id='01007EF00011E000')
        self.store.save([old]);other=self.root/'Other [01006A800016E000].nsp';other.write_bytes(b'rom')
        with self.assertRaises(ValueError):rom_locations.relocate(old,other,self.store)
        self.assertEqual(self.store.load()[0].source,'/old.nsp')
    def test_forget_removes_only_reference_and_does_not_reimport_pending_steam(self):
        account=self.root/'account';self.entry.metadata.update(steam_account=str(account),steam_appid=123);self.store.save([self.entry])
        save=self.store.root/'saves/game.sav';save.parent.mkdir();save.write_bytes(b'SAVE')
        result=rom_locations.forget(self.entry,self.store,start_worker=False)
        self.assertEqual(result['state'],'pending');self.assertFalse(self.store.load());self.assertEqual(save.read_bytes(),b'SAVE')
        item={'appid':123,'name':'Game','exe':'dolphin','options':str(self.rom),'account':str(account),'startdir':'','icon':''}
        with patch.object(steam_inventory,'shortcuts',return_value=[item]):
            entries=steam_inventory.merge_steam([],account=account,ignored_shortcuts=rom_locations.ignored_shortcuts(self.store))
        self.assertEqual(entries,[])
        self.assertEqual(rom_locations.filter_forgotten([self.entry],self.store),[])
        self.rom.parent.mkdir();self.rom.write_bytes(b'back')
        self.assertEqual(rom_locations.filter_forgotten([self.entry],self.store),[self.entry])
    def test_shared_steam_shortcut_is_not_deleted(self):
        self.entry.metadata.update(steam_account='account',steam_appid=123)
        other=Entry('Other',['dolphin','/other.iso'],'emulated','Wii','/other.iso',metadata=dict(self.entry.metadata))
        self.store.save([self.entry,other])
        with self.assertRaises(ValueError):rom_locations.forget(self.entry,self.store,start_worker=False)
        self.assertEqual(len(self.store.load()),2);self.assertFalse((self.store.root/'pending.json').exists())

    def test_failed_queue_keeps_library_and_rolls_back_guard(self):
        with patch('deck_library.port_removal.prepare_steam',side_effect=OSError('full disk')):
            with self.assertRaises(OSError):rom_locations.forget(self.entry,self.store,start_worker=False)
        self.assertEqual(self.store.load()[0].id,self.entry.id);self.assertEqual(rom_locations.forgotten(self.store),[])
