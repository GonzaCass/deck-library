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
    def test_switch_base_is_bound_to_unknown_titles_without_changing_catalog(self):
        entry=Entry('Other',['/bin/true'],platform='Switch',game_id='0100abcdef120000')
        values=presets.recommended(entry,self.store)
        self.assertEqual(len(values),3);value=values[0]
        self.assertEqual(len({json.dumps(v['settings'],sort_keys=True) for v in values}),3)
        self.assertEqual([v['name'] for v in values],['Switch — Equilibrado','Switch — Rendimiento','Switch — Compatibilidad'])
        for v in values:self.assertTrue(presets.compatible(entry,v));self.assertEqual(v['tested']['status'],'proposal')
        self.assertEqual(value['game'],{'id':'0100ABCDEF120000','name':'Other','platform':'Switch'})
        self.assertEqual(value['id'],'eden-0100abcdef120000-default')
        self.assertEqual(value['tested']['status'],'proposal');self.assertTrue(presets.compatible(entry,value))
        self.assertFalse(value['settings']['System']['use_docked_mode'])
        self.assertEqual(value['settings']['Core']['speed_limit'],100)
        value['settings']['Renderer']['resolution_setup']=1
        self.assertEqual(presets.recommended(entry,self.store)[0]['settings']['Renderer']['resolution_setup'],3)
        self.assertEqual(self.profile('eden-switch-default')['game']['id'],'switch-default')
        self.assertFalse((self.store.root/'presets').exists())
    def test_switch_specific_bundled_and_imported_profiles_take_precedence(self):
        for value in self.catalog:
            if value['adapter']['id']!='eden' or value['id'] in presets.SWITCH_BASES:continue
            entry=Entry(value['game']['name'],['/bin/true'],platform='Switch',game_id=value['game']['id'])
            self.assertEqual(presets.recommended(entry,self.store),[value])
        entry=Entry('Other',['/bin/true'],platform='Switch',game_id='0100ABCDEF120000')
        value=presets.recommended(entry,self.store)[0];value['id']='community-other'
        path=self.root/'import.json';path.write_text(json.dumps(value));presets.import_preset(path,self.store)
        self.assertEqual(presets.recommended(entry,self.store),[value])
    def test_switch_base_requires_title_id_and_eden_and_resolves_filename_ids(self):
        for entry in (Entry('Unknown',['/bin/true'],platform='Switch',source=str(self.root/'Unknown.nsp')),Entry('Other',['/bin/true'],platform='Linux',game_id='0100ABCDEF120000'),Entry('Other',['/bin/true'],platform='Switch',game_id='0100ABCDEF120000',metadata={'adapter':'dolphin'})):
            self.assertEqual(presets.recommended(entry,self.store),[])
        entry=Entry('Other',['/bin/true'],platform='Switch',source=str(self.root/'Other [0100ABCDEF120800].nsp'))
        self.assertEqual(presets.recommended(entry,self.store)[0]['game']['id'],'0100ABCDEF120000')
    def test_switch_base_apply_export_restore_and_version_guard(self):
        config=self.root/'eden';config.mkdir();global_path=config/'qt-config.ini';global_path.write_text('[Controls]\nplayer_0_button_a=GLOBAL\n')
        entry=Entry('Other',['/bin/true'],platform='Switch',game_id='0100ABCDEF120000',metadata={'emulator_version':'0.2.1'})
        profile=presets.recommended(entry,self.store)[0];target=presets.target_for(entry,config)
        original='[Controls]\nplayer_0_button_a=KEEP\n[System]\nlanguage_index=5\n[Data%20Storage]\nnand_directory=/PRIVATE/NAND\n[Renderer]\nresolution_setup=5\nresolution_setup\\use_global=true\n'
        for existing in (False,True):
            with self.subTest(existing=existing),patch('deck_library.presets.emulator_busy',return_value=False):
                if existing:target.parent.mkdir(parents=True,exist_ok=True);target.write_text(original)
                presets.apply(entry,profile,self.store,config);parser=presets.ini_parser(target.read_text())
                for section,options in profile['settings'].items():
                    for key,value in options.items():
                        self.assertEqual(parser[section][key],presets.scalar(value))
                        self.assertEqual(parser[section][key+'\\use_global'],'false');self.assertEqual(parser[section][key+'\\default'],'false')
                if existing:
                    self.assertEqual(parser['Controls']['player_0_button_a'],'KEEP');self.assertEqual(parser['System']['language_index'],'5');self.assertEqual(parser['Data%20Storage']['nand_directory'],'/PRIVATE/NAND')
                exported=presets.export_current(entry,'Test','Alias',self.store,config)
                self.assertEqual(exported['game']['id'],entry.game_id);self.assertNotIn('/PRIVATE',json.dumps(exported))
                presets.restore(entry,self.store)
                self.assertEqual(target.exists(),existing)
                if existing:self.assertEqual(target.read_text(),original)
                self.assertEqual(global_path.read_text(),'[Controls]\nplayer_0_button_a=GLOBAL\n')
        entry.metadata['emulator_version']='9.0'
        with patch('deck_library.presets.emulator_busy',return_value=False),self.assertRaisesRegex(ValueError,'versión instalada'):
            presets.apply(entry,profile,self.store,config)
        self.assertEqual(target.read_text(),original)
    def test_catalog_document_matches_bundled_profiles(self):
        document=json.loads((pathlib.Path(__file__).resolve().parents[1]/'presets/catalog.json').read_text())
        self.assertEqual({p['id']:p for p in document['presets']},{p['id']:p for p in self.catalog})
    def test_best_profile_is_local_persistent_and_specific_to_the_game(self):
        entry=Entry('Other',['/bin/true'],platform='Switch',game_id='0100ABCDEF120000')
        values=presets.recommended(entry,self.store)
        self.assertEqual(presets.best_for(entry,self.store),'')
        presets.mark_best(entry,values[1],self.store)
        self.assertEqual(presets.best_for(entry,Store(self.store.root)),values[1]['id'])
        self.assertEqual(presets.recommended(entry,self.store),values)
        self.assertFalse((self.store.root/'applied-presets').exists())
        other=Entry('Other 2',['/bin/true'],platform='Switch',game_id='0100ABCDEF122000')
        self.assertEqual(presets.best_for(other,self.store),'')
        with self.assertRaises(ValueError):presets.mark_best(other,values[1],self.store)
        presets.mark_best(entry,values[2],self.store)
        self.assertEqual(presets.best_for(entry,self.store),values[2]['id'])
        entry.game_id=other.game_id
        self.assertEqual(presets.best_for(entry,self.store),'')
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
