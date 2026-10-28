import os,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import ports,switch_extract as sx,switch_port
from deck_library.models import Store,Entry,atomic_json

class SwitchPortFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.home=pathlib.Path(self.temp.name);self.store=Store(self.home/'data')
        self.dump=self.home/'dump';(self.dump/'exefs').mkdir(parents=True);(self.dump/'exefs/main').write_bytes(b'NSO0');(self.dump/'romfs').mkdir()
    def tearDown(self):self.temp.cleanup()
    def test_a_dump_root_or_either_child_can_be_selected_without_keys_or_conversion(self):
        for path in (self.dump,self.dump/'exefs',self.dump/'romfs'):self.assertEqual(sx.extracted_folder(path),self.dump)
        with self.assertRaises(ValueError):sx.extracted_folder(self.home)
    def test_savage_wind_accepts_originals_and_passes_them_to_its_first_run_builder(self):
        item=ports.clean({'name':'Savage Wind','repository':'ReviveDX/SavageWindRecomp'})
        self.assertEqual(item['setup'],'switch_launcher')
        folder=ports.ports_root(self.home)/'savage';folder.mkdir(parents=True);exe=folder/'game.AppImage';exe.write_bytes(b'ELF')
        record={**item,'folder':'savage','executable':exe.name,'runtime':'linux','configured':False,'tag':'v0.3.0-alpha.3'}
        atomic_json(self.store.root/'ports.json',{item['repository']:record});ports.set_input(item['repository'],'original_data',self.dump,self.store)
        with patch.object(ports,'ports_root',return_value=folder.parent):
            ready=ports.configure(item['repository'],self.store,home=self.home,progress=lambda _:None)
        self.assertTrue(ready['configured']);self.assertTrue((self.dump/'exefs/main').exists())
        entry=ports.entry_for(folder);env=switch_port.launch_environment(entry,{},self.store,home=self.home)
        self.assertEqual(env['SAVAGEWIND_LAUNCHER_SETUP'],str(self.dump));self.assertEqual(env['SAVAGEWIND_LAUNCHER_MODE'],'setup')
        extracted=self.home/'.local/share/savagewind/extracted'
        for name in ('exefs/main','romfs.bin','swgame.so'):
            target=extracted/name;target.parent.mkdir(parents=True,exist_ok=True);target.touch()
        self.assertEqual(switch_port.launch_environment(entry,{},self.store,home=self.home),{})
        self.assertEqual(switch_port.launch_environment(Entry('Other',['/bin/true']),{},self.store,home=self.home),{})
    def test_bundled_binary_has_the_pinned_hash_and_executes_on_the_deck_platform(self):
        import platform
        if platform.system()!='Linux' or platform.machine().lower() not in ('x86_64','amd64'):self.skipTest('Linux x86-64 bundle')
        path=sx.bundled_tool();self.assertTrue(path);self.assertTrue(os.access(path,os.X_OK));self.assertTrue(sx.is_nstool(path))

    def test_existing_savage_wind_installs_gain_the_wizard_without_resetting_a_prepared_game(self):
        repository='ReviveDX/SavageWindRecomp'
        old={'folder':'savage','runtime':'linux','setup':'','configured':False}
        atomic_json(self.store.root/'ports.json',{repository:old})
        with patch.object(switch_port,'prepared',return_value=False):
            record=ports.records(self.store)[repository];self.assertEqual(record['setup'],'switch_launcher');self.assertFalse(record['configured'])
        with patch.object(switch_port,'prepared',return_value=True):self.assertTrue(ports.records(self.store)[repository]['configured'])
        import json
        self.assertEqual(json.loads((self.store.root/'ports.json').read_text())[repository],old)
