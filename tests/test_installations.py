import json,pathlib,tempfile,unittest,threading,time,sys
from unittest.mock import patch
from deck_library.discovery import scan,prism_entries
from deck_library.installations import emudeck_paths
from deck_library.models import Entry,Store
from deck_library.setup_wii import check_image,run_logged,Cancelled

class InstallationTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_reads_emudeck_custom_paths_without_evaluating_shell(self):
        config=self.root/'.config/EmuDeck';config.mkdir(parents=True);(config/'settings.sh').write_text('emulationPath="$HOME"/CustomEmu\nromsPath="/SD/Games"\nsavesPath=$(touch /UNSAFE)\n')
        result=emudeck_paths(self.root);self.assertTrue(result['installed']);self.assertEqual(result['roms'],'/SD/Games');self.assertEqual(result['root'],str(self.root/'CustomEmu'));self.assertNotIn('UNSAFE',str(result))
    def test_prism_instances_are_named_by_folder_id_and_keep_account_data_private(self):
        root=self.root/'.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher';folder=root/'instances/folder with spaces';folder.mkdir(parents=True);(folder/'instance.cfg').write_text('[General]\nname=Display Name\niconKey=icon\n');(root/'prismlauncher.cfg').write_text('[General]\nInstanceDir=instances\n');(root/'accounts.json').write_text('PRIVATE TOKEN')
        (folder/'mmc-pack.json').write_text('{"components":[{"uid":"net.minecraft","version":"1.21.1"}]}')
        found=prism_entries(self.root);self.assertEqual(len(found),1);entry=found[0];self.assertEqual(entry.name,'Display Name');self.assertEqual(entry.command[-2:],['--launch','folder with spaces']);self.assertEqual(entry.game_id,'minecraft-java');self.assertNotIn('PRIVATE TOKEN',json.dumps(entry.to_dict()))
    def test_new_launcher_detection_preserves_the_old_steam_identity(self):
        store=Store(self.root/'data');old=Entry('Game',['/old/emulator','-g','/ROM'],kind='emulated',platform='Switch',source='/ROM',mods=False);store.save([old]);new=Entry('Game',['/new/emulator','-g','/ROM'],kind='emulated',platform='Switch',source='/ROM',game_id='0100152000022000');store.merge([new],overwrite=False)
        saved=store.load();self.assertEqual(len(saved),1);self.assertEqual(saved[0].id,old.id);self.assertFalse(saved[0].mods);self.assertEqual(saved[0].command,new.command);self.assertEqual(saved[0].game_id,new.game_id)
    def test_wii_wizard_rejects_wrong_disc_before_installing(self):
        path=self.root/'wrong.iso';path.write_bytes(b'RMCE01')
        with self.assertRaises(ValueError):check_image(path)
        path.write_bytes(b'RMCP01');self.assertEqual(check_image(path),path.resolve())
    def test_cancel_stops_the_owned_setup_process(self):
        event=threading.Event();timer=threading.Timer(.2,event.set);timer.start();start=time.monotonic()
        with (self.root/'install.log').open('w') as log:
            with self.assertRaises(Cancelled):run_logged([sys.executable,'-c','import time; time.sleep(30)'],self.root,{},log,lambda _:None,event)
        timer.join();self.assertLess(time.monotonic()-start,5)
