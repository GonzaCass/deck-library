import configparser,copy,json,pathlib,tempfile,unittest,io
from unittest.mock import patch
from deck_library.models import Entry,Store
from deck_library import presets

class PresetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data')
        self.catalog=presets.catalog(self.store)
    def tearDown(self):self.tmp.cleanup()
    def profile(self,id_):return copy.deepcopy(next(p for p in self.catalog if p['id']==id_))
    def test_all_bundled_profiles_validate_and_ids_are_unique(self):
        self.assertGreaterEqual(len(self.catalog),7);self.assertEqual(len({p['id'] for p in self.catalog}),len(self.catalog))
        for value in self.catalog:presets.validate(value)
    def test_rejects_commands_paths_bad_types_and_speed_hacks(self):
        for update in ({'shell':'curl anything'},{'paths':{'dvd_root':'/evil'}},{'video':{'resolution_multiplier':True}},{'video':{'frame_interpolation_fps':90}}):
            value=self.profile('wiicompiled-rmcp01-sharp');value['settings']=update
            with self.assertRaises(ValueError):presets.validate(value)
        value=self.profile('eden-smash-sharp');value['settings']['Core']['speed_limit']=150
        with self.assertRaises(ValueError):presets.validate(value)
        value=self.profile('wiicompiled-rmcp01-sharp');value['id']='../../unsafe'
        with self.assertRaises(ValueError):presets.validate(value)
    def test_wii_apply_export_and_restore_preserve_paths_and_controls(self):
        config=self.root/'Config.toml';original='[paths]\ndvd_root="/PRIVATE/GAME"\n[video]\nresolution_multiplier=1.0\n[controls]\nbutton_a="KEEP"\n';config.write_text(original)
        entry=Entry('Wii',['/bin/true'],kind='wiicompiled',platform='WiiCompiled',game_id='RMCP01',metadata={'adapter':'wiicompiled','config':str(config),'build':'0.2.33'})
        with patch('deck_library.presets.emulator_busy',return_value=False):
            presets.apply(entry,self.profile('wiicompiled-rmcp01-sharp'),self.store)
            export=presets.export_current(entry,'Test','Alias',self.store)
            self.assertNotIn('/PRIVATE',json.dumps(export));self.assertNotIn('controls',export['settings']);self.assertEqual(export['settings']['video']['resolution_multiplier'],1.5)
            self.assertIn('button_a="KEEP"',config.read_text());self.assertIn('dvd_root="/PRIVATE/GAME"',config.read_text())
            presets.restore(entry,self.store)
        self.assertEqual(config.read_text(),original)
    def test_eden_per_game_flags_and_other_values_are_preserved(self):
        config=self.root/'eden';(config/'custom').mkdir(parents=True);target=config/'custom/01006A800016E000.ini';target.write_text('[Controls]\nplayer_0_button_a=KEEP\n[Renderer]\nresolution_setup=2\n')
        entry=Entry('Smash',['/bin/true'],platform='Switch',game_id='01006A800016E000')
        with patch('deck_library.presets.emulator_busy',return_value=False):presets.apply(entry,self.profile('eden-smash-sharp'),self.store,config)
        value=target.read_text();self.assertIn('player_0_button_a=KEEP',value);self.assertIn('resolution_setup=3',value);self.assertIn('resolution_setup\\use_global=false',value);self.assertIn('resolution_setup\\default=false',value)
    def test_wrong_game_version_busy_process_and_changed_config_are_rejected(self):
        config=self.root/'Config.toml';config.write_text('[video]\nresolution_multiplier=1.0\n')
        entry=Entry('Wii',['/bin/true'],platform='WiiCompiled',game_id='RMCP01',metadata={'adapter':'wiicompiled','config':str(config),'build':'9.0'})
        with patch('deck_library.presets.emulator_busy',return_value=False):
            with self.assertRaises(ValueError):presets.apply(entry,self.profile('wiicompiled-rmcp01-sharp'),self.store)
        entry.metadata['build']='0.2.33'
        with patch('deck_library.presets.emulator_busy',return_value=True):
            with self.assertRaises(RuntimeError):presets.apply(entry,self.profile('wiicompiled-rmcp01-sharp'),self.store)
        with patch('deck_library.presets.emulator_busy',return_value=False):
            presets.apply(entry,self.profile('wiicompiled-rmcp01-sharp'),self.store);config.write_text(config.read_text()+'# external change\n')
            with self.assertRaises(ValueError):presets.restore(entry,self.store)
        other=Entry('Other',['/bin/true'],platform='Switch',game_id='0100152000022000')
        with self.assertRaises(ValueError):presets.preview(other,self.profile('eden-smash-sharp'))
    def test_feedback_has_no_local_paths_or_accounts(self):
        entry=Entry('Wii',['/bin/true'],platform='WiiCompiled',game_id='RMCP01',source='/PRIVATE/PATH')
        report=presets.feedback(entry,self.profile('wiicompiled-rmcp01-sharp'),'works','Todo bien',self.store)
        self.assertNotIn('/PRIVATE',json.dumps(report));self.assertEqual(report['game_id'],'RMCP01')
    def test_bad_remote_catalog_does_not_install_even_its_valid_entries(self):
        good=self.profile('wiicompiled-rmcp01-sharp');bad=copy.deepcopy(good);bad['settings']['paths']={'dvd_root':'/unsafe'}
        response=io.BytesIO(json.dumps({'schema_version':1,'presets':[good,bad]}).encode());response.url='https://example.test/catalog.json'
        with patch('urllib.request.urlopen',return_value=response):
            with self.assertRaises(ValueError):presets.refresh_catalog(response.url,self.store)
        self.assertFalse((self.store.root/'presets').exists())
