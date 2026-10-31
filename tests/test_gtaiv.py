import hashlib
import pathlib
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from deck_library import gtaiv
from deck_library.models import Store
from deck_library.service import queue_entries

class GTAIVTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.temp.name)
        self.root=self.base/'Game/GTAIV';self.root.mkdir(parents=True)
        self.exe=b'MZ'+b'\0'*8+struct.pack('<IIII',0xfeef04bd,65536,65538,59)
        (self.root/'GTAIV.exe').write_bytes(self.exe)
        self.settings=self.base/'Settings/SETTINGS.CFG';self.settings.parent.mkdir()
        data=bytearray(1469);data[:4]=b'\x12\x15\x28\x10';struct.pack_into('<I',data,608,1);data[900:904]=b'KEEP'
        self.settings.write_bytes(data);self.original=bytes(data)
        self.store=Store(self.base/'private');self.archive=self.base/'mod.zip'
        self.payload={'plugins/GTAIV.EFLC.FusionFix.asi':b'old-asi','vulkan.dll':b'dxvk','d3d9.dll':b'wrapper','dinput8.dll':b'loader',gtaiv.INI:b'[MAIN]\nRecoilFix = 1\n[USERPROFILE]\nCustomUserProfilePath =\n'}
        with zipfile.ZipFile(self.archive,'w') as z:
            for n,b in self.payload.items():z.writestr(n,b)
        self.sha=patch.object(gtaiv,'SHA256',hashlib.sha256(self.archive.read_bytes()).hexdigest());self.sha.start()
        self.closed=patch.object(gtaiv,'busy',return_value=False);self.closed.start()
    def tearDown(self):self.closed.stop();self.sha.stop();self.temp.cleanup()
    def apply(self):return gtaiv.apply(self.root,self.settings,self.store,self.archive)
    def seed(self):
        for n,data in {gtaiv.CFG:b'[FRAMELIMIT]\nFpsLimitPreset = 9\n[MISC]\nAntialiasing = 7\n',gtaiv.INI:b'[MAIN]\nRecoilFix = 0\n',next(iter(gtaiv.REMOVED)):b'new-version-only','dxvk.conf':b'dxvk.hud = fps\nd3d9.presentInterval = 0\n','plugins/GTAIV.EFLC.FusionFix.asi':b'new-asi'}.items():
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def test_apply_restore_preserves_user_choices_and_absence(self):
        original=self.seed();backup=self.apply()
        cfg=(self.root/gtaiv.CFG).read_text()
        self.assertIn('FpsLimitPreset = 9',cfg);self.assertIn('Antialiasing = 7',cfg);self.assertIn('Buttons = 9',cfg)
        self.assertIn('RecoilFix = 0',(self.root/gtaiv.INI).read_text())
        dx=(self.root/'dxvk.conf').read_text();self.assertIn('dxvk.hud = fps',dx);self.assertIn(gtaiv.DXVK,dx)
        expected=bytearray(self.original);struct.pack_into('<I',expected,608,0)
        self.assertEqual(self.settings.read_bytes(),expected)
        self.assertTrue(all(not (self.root/n).exists() for n in gtaiv.REMOVED))
        self.assertEqual(gtaiv.restore(self.root,self.store),backup)
        self.assertEqual({str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},original)
        self.assertEqual(self.settings.read_bytes(),self.original)
    def test_latest_recipe_resets_old_menu_ids_and_restores_exact_files(self):
        original=self.seed()
        with patch.object(gtaiv,'LATEST_SHA256',hashlib.sha256(self.archive.read_bytes()).hexdigest()):
            backup=gtaiv.apply(self.root,self.settings,self.store,self.archive,release='5.1.2')
        self.assertEqual(gtaiv.installed_release(self.root,self.store),'5.1.2')
        cfg=(self.root/gtaiv.CFG).read_text()
        self.assertIn('FpsLimitPreset = 5',cfg);self.assertIn('Antialiasing = 2',cfg);self.assertIn('Buttons = 4',cfg)
        self.assertNotIn('Antialiasing = 7',cfg)
        import json
        self.assertEqual(json.loads((pathlib.Path(backup)/'record.json').read_text())['version'],'5.1.2')
        gtaiv.restore(self.root,self.store)
        self.assertEqual({str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},original)

    def test_invalid_archive_busy_version_and_symlink_write_nothing(self):
        with patch.object(gtaiv,'busy',return_value=True),self.assertRaises(RuntimeError):self.apply()
        with patch.object(gtaiv,'SHA256','wrong'),self.assertRaises(ValueError):self.apply()
        (self.root/'GTAIV.exe').write_bytes(b'MZ')
        with self.assertRaises(ValueError):self.apply()
        (self.root/'GTAIV.exe').write_bytes(self.exe)
        outside=self.base/'outside';outside.mkdir();(self.root/'plugins').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):self.apply()
        self.assertFalse(list(outside.iterdir()));self.assertEqual(self.settings.read_bytes(),self.original)
    def test_failure_during_install_rolls_back(self):
        original=self.seed();real=gtaiv.write;count=[0]
        def fail(path,data):
            if str(path).startswith(str(self.root)):
                count[0]+=1
                if count[0]==3:raise OSError('disk error')
            return real(path,data)
        with patch.object(gtaiv,'write',side_effect=fail),self.assertRaises(OSError):self.apply()
        self.assertEqual({str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},original)
        self.assertEqual(self.settings.read_bytes(),self.original)
    def test_restore_refuses_changes_after_game_saves_settings(self):
        self.apply();self.settings.write_bytes(self.original)
        with self.assertRaises(ValueError):gtaiv.restore(self.root,self.store)
        self.assertEqual((self.root/'vulkan.dll').read_bytes(),b'dxvk')
    def test_restore_after_playing_can_archive_changed_settings(self):
        original=self.seed();self.apply()
        (self.root/gtaiv.CFG).write_text('[MISC]\nAntialiasing = 2\n')
        self.settings.write_bytes(self.original)
        gtaiv.restore(self.root,self.store,preserve_current_settings=True)
        archived=list(gtaiv.state_path(self.root,self.store).glob('before-restore-*/files/'+gtaiv.CFG))
        self.assertEqual(len(archived),1);self.assertIn('Antialiasing = 2',archived[0].read_text())
        self.assertEqual((self.root/gtaiv.CFG).read_bytes(),original[gtaiv.CFG])

    def test_discovery_micro_sd_and_official_games_not_queued_as_shortcuts(self):
        home=self.base/'home';steam=home/'.local/share/Steam';(steam/'steamapps').mkdir(parents=True)
        library=self.base/'SD library';game=library/'steamapps/common/Grand Theft Auto IV/GTAIV';game.mkdir(parents=True);(game/'GTAIV.exe').write_bytes(self.exe)
        (steam/'steamapps/libraryfolders.vdf').write_text('"path" "'+str(library)+'"')
        (library/'steamapps/appmanifest_12210.acf').write_text('"installdir" "Grand Theft Auto IV"')
        entry=gtaiv.discover(home)[0];self.assertEqual(entry.metadata['gtaiv_root'],str(game));self.assertTrue(entry.metadata['steam_store'])
        self.assertEqual(queue_entries([entry],self.base/'account',self.store,start_worker=False)['count'],0)
        self.assertFalse((self.store.root/'pending.json').exists())

if __name__=='__main__':unittest.main()
