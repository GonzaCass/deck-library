import json,pathlib,tempfile,tomllib,unittest
from unittest.mock import patch
from deck_library import presets,profile_capture,profile_display
from deck_library.models import Entry,Store

class NarutoPresetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'private')
        self.config=self.root/'narutorise.toml';self.original='renderer = "native"\nnative_backend = "vulkan"\nframe_rate = 60\nuser_language = 5\ntranslation_mod = "KEEP"\nkeybind_a = "KEEP"\npath = "/PRIVATE"\n[private]\ntoken = "SECRET"\n';self.config.write_text(self.original)
        (self.root/'narutorise.version').write_text('0.3.0-beta\n')
        self.entry=Entry('Naruto: Rise of a Ninja',['/bin/true'],source=str(self.root/'narutorise_launcher.exe'),platform='Windows',metadata={'port_repository':'jorjbarbosa/naruto-rise-recomp'})
    def profiles(self):return presets.recommended(self.entry,self.store)
    def test_three_profiles_only_confirm_the_configuration_the_user_played(self):
        values=self.profiles();self.assertEqual([p['name'].split(' — ')[1] for p in values],['Equilibrado','Rendimiento','Calidad']);self.assertEqual([p['tested']['status'] for p in values],['user-confirmed','proposal','proposal'])
        self.assertEqual(presets.public_game_id(self.entry),'555307E5');self.assertTrue(all(presets.is_bundled(v) and presets.automatic(v) for v in values))
        other=Entry('Naruto',['/bin/true'],source=self.entry.source,metadata={'port_repository':'jorjbarbosa/broken-bond-recomp'})
        self.assertFalse(presets.compatible(other,values[0]))
    def test_apply_restore_keep_language_controls_private_data_and_settings_sections(self):
        value=self.profiles()[1]
        with patch.object(presets,'busy',return_value=False):
            presets.apply(self.entry,value,self.store)
            data=tomllib.loads(self.config.read_text());self.assertFalse(data['vsync']);self.assertEqual(data['swap_post_effect'],'none');self.assertEqual(data['user_language'],5);self.assertEqual(data['translation_mod'],'KEEP');self.assertEqual(data['keybind_a'],'KEEP');self.assertEqual(data['private']['token'],'SECRET')
            presets.restore(self.entry,self.store)
        self.assertEqual(self.config.read_text(),self.original)
    def test_capture_and_import_only_graphics_and_detect_the_installed_version(self):
        with patch.object(profile_capture,'runtime_info',return_value={'kind':'proton','version':'Proton 11.0'}):value=presets.export_current(self.entry,'Test','Alias',self.store)
        self.assertEqual(value['adapter']['versions'],['0.3.0-beta']);self.assertEqual(value['settings']['runtime']['frame_rate'],60)
        self.assertNotIn('/PRIVATE',json.dumps(value));self.assertNotIn('SECRET',json.dumps(value));self.assertNotIn('user_language',json.dumps(value));self.assertNotIn('keybind',json.dumps(value))
        self.assertEqual(profile_capture.read_file(self.entry,self.config),value['settings'])
    def test_busy_and_changed_versions_refuse_to_write(self):
        value=self.profiles()[0]
        with patch.object(presets,'busy',return_value=True),self.assertRaises(RuntimeError):presets.apply(self.entry,value,self.store)
        (self.root/'narutorise.version').write_text('0.4.0-beta')
        with patch.object(presets,'busy',return_value=False),self.assertRaisesRegex(ValueError,'versión instalada'):presets.apply(self.entry,value,self.store)
        self.assertEqual(self.config.read_text(),self.original)
    def test_profile_details_compare_typed_root_toml_and_show_resolution(self):
        profile=self.profiles()[0];_,changes=profile_display.differences(self.entry,profile)
        self.assertFalse(any(key=='runtime.frame_rate' for key,_,_ in changes));self.assertIn(('Resolución','1× (720p)'),profile_display.highlights(profile))
