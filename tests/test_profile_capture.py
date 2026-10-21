import json,pathlib,tempfile,time,unittest
from unittest.mock import patch
from deck_library.models import Entry,Store
from deck_library import presets,profile_capture
from community.server import API,digest

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'library')
        self.home=patch('pathlib.Path.home',return_value=self.root);self.home.start()
    def tearDown(self):self.home.stop();self.temp.cleanup()
    def file(self,name,content):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content);return p
    def test_eden_captures_effective_global_and_local_without_paths(self):
        config=self.root/'eden';self.file('eden/qt-config.ini','[Renderer]\nresolution_setup=3\nanti_aliasing=1\n[Controls]\naccount=SECRET\n[Data Storage]\npath=/PRIVATE\n')
        self.file('eden/custom/0100000000000000.ini','[Renderer]\nresolution_setup=5\nresolution_setup\\use_global=true\nanti_aliasing=2\nanti_aliasing\\use_global=false\n')
        e=Entry('Game',['eden'],platform='Switch',game_id='0100000000000000')
        value=presets.export_current(e,'Test','Alias',self.store,config)
        self.assertEqual(value['settings'],{'Renderer':{'resolution_setup':3,'anti_aliasing':2}})
        self.assertNotIn('SECRET',json.dumps(value));self.assertNotIn('/PRIVATE',json.dumps(value))
    def test_eden_no_custom_file_still_captures_globals(self):
        self.file('eden/qt-config.ini','[Renderer]\nresolution_setup=4\n')
        e=Entry('Game',['eden'],platform='Switch',game_id='0100000000000000')
        self.assertEqual(presets.current_values(e,self.root/'eden')['Renderer']['resolution_setup'],4)
        self.assertFalse((self.root/'eden/custom').exists())
    def test_duckstation_global_and_override(self):
        self.file('.local/share/duckstation/settings.ini','[GPU]\nResolutionScale=3\nPGXPEnable=true\n')
        self.file('.local/share/duckstation/gamesettings/SLUS-00875.ini','[GPU]\nResolutionScale=4\n')
        e=Entry('Game',['duckstation'],platform='PlayStation',game_id='SLUS-00875')
        self.assertEqual(presets.current_values(e)['GPU'],{'ResolutionScale':4,'PGXPEnable':True})
    def test_dolphin_reads_graphics_globals_under_game_sections(self):
        self.file('.config/dolphin-emu/GFX.ini','[Settings]\nInternalResolution=2\nMSAA=4\n[Hacks]\nEFBScaledCopy=True\n')
        self.file('.local/share/dolphin-emu/GameSettings/RMCP01.ini','[Video_Settings]\nInternalResolution=3\n')
        e=Entry('Game',['dolphin-emu'],platform='Wii',game_id='RMCP01')
        self.assertEqual(presets.current_values(e),{'Video_Settings':{'InternalResolution':3,'MSAA':4},'Video_Hacks':{'EFBScaledCopy':True}})
    def test_pcsx2_capture_and_apply_only_identified_per_game_file(self):
        self.file('.config/PCSX2/inis/PCSX2.ini','[EmuCore/GS]\nupscale_multiplier=2\nMaxAnisotropy=4\n[Folders]\nBios=/PRIVATE\n')
        target=self.file('.config/PCSX2/gamesettings/SLUS-21285_FDD12792.ini','[EmuCore/GS]\nupscale_multiplier=3\n[Controls]\nPad=KEEP\n')
        e=Entry('Game',['pcsx2'],platform='PlayStation 2',game_id='SLUS-21285')
        value=presets.export_current(e,'Test','Alias',self.store);self.assertEqual(value['settings']['EmuCore/GS']['upscale_multiplier'],3.0)
        self.assertNotIn('/PRIVATE',json.dumps(value));value['settings']['EmuCore/GS']['upscale_multiplier']=4.0
        with patch('deck_library.presets.busy',return_value=False):
            presets.apply(e,value,self.store);self.assertIn('upscale_multiplier=4.0',target.read_text());self.assertIn('Pad=KEEP',target.read_text());presets.restore(e,self.store)
        self.assertIn('upscale_multiplier=3',target.read_text())
        self.file('.config/PCSX2/gamesettings/SLUS-21285_00000000.ini','')
        with self.assertRaises(ValueError):presets.target_for(e)
    def test_pcsx2_without_serial_captures_globals_but_cannot_write_them(self):
        global_=self.file('.config/PCSX2/inis/PCSX2.ini','[EmuCore/GS]\nupscale_multiplier=2\n')
        e=Entry('Unknown',['pcsx2'],platform='PlayStation 2');value=presets.export_current(e,'Test','Alias',self.store)
        self.assertEqual(value['settings']['EmuCore/GS']['upscale_multiplier'],2)
        with self.assertRaises(ValueError):presets.apply(e,value,self.store)
        self.assertEqual(global_.read_text(),'[EmuCore/GS]\nupscale_multiplier=2\n')
    def test_azahar_inheritance_and_apply_flags(self):
        self.file('.config/azahar/qt-config.ini','[Renderer]\nresolution_factor=2\nuse_vsync_new=true\n')
        target=self.file('.config/azahar/custom/0004000000123400.ini','[Renderer]\nresolution_factor=5\nresolution_factor\\use_global=true\n')
        e=Entry('Game',['azahar'],platform='Nintendo 3DS',game_id='0004000000123400')
        value=presets.export_current(e,'Test','Alias',self.store);self.assertEqual(value['settings']['Renderer']['resolution_factor'],2)
        value['settings']['Renderer']['resolution_factor']=3
        with patch('deck_library.presets.busy',return_value=False):presets.apply(e,value,self.store)
        self.assertIn('resolution_factor\\use_global=false',target.read_text())
    def test_mgba_is_read_only_reference(self):
        global_=self.file('.config/mgba/config.ini','[ports.qt]\nvideoScale=3\ninterframeBlending=1\npath=/PRIVATE\n')
        e=Entry('Game',['mgba'],platform='Game Boy Advance');value=presets.export_current(e,'Test','Alias',self.store)
        self.assertEqual(value['settings'],{'ports.qt':{'videoScale':3,'interframeBlending':True}})
        self.assertFalse(presets.automatic(value))
        with self.assertRaises(ValueError):presets.apply(e,value,self.store)
        self.assertIn('path=/PRIVATE',global_.read_text());self.assertNotIn('/PRIVATE',json.dumps(value))
    def test_ppsspp_game_overrides_and_native_target(self):
        self.file('.config/ppsspp/PSP/SYSTEM/ppsspp.ini','[Graphics]\nInternalResolution=2\nAnisotropyLevel=4\n')
        target=self.file('.config/ppsspp/PSP/SYSTEM/ULUS10567_ppsspp.ini','[Graphics]\nInternalResolution=3\n')
        e=Entry('Game',['PPSSPPSDL'],platform='PSP',game_id='ULUS10567')
        value=presets.export_current(e,'Test','Alias',self.store);self.assertEqual(value['settings']['Graphics'],{'InternalResolution':3,'AnisotropyLevel':4})
        self.assertEqual(presets.target_for(e),target)
    def test_manual_guides_are_per_game_and_never_executed(self):
        e=Entry('Port',['port'],platform='Windows',metadata={'port_repository':'author/project'})
        value=presets.export_current(e,'Guide','Alias',self.store);value['instructions']='WINEDLLOVERRIDES=dinput8=n,b %command%';value['runtime']={'kind':'proton','version':'Proton 9.0','launch_options':'echo text'}
        presets.validate(value);self.assertTrue(presets.compatible(e,value));self.assertFalse(presets.automatic(value))
        with patch('subprocess.Popen') as launch,self.assertRaises(ValueError):presets.apply(e,value,self.store)
        launch.assert_not_called();self.assertFalse(presets.compatible(Entry('Other',['other']),value))
    def test_reeot_guides_do_not_reuse_legacy_settings(self):
        e=Entry('Spider-Man',['project2099'],platform='Windows',game_id='415608B2',metadata={'adapter':'project2099','engine':'reeot'})
        value=presets.export_current(e,'Guide','Alias',self.store);self.assertTrue(presets.compatible(e,value));self.assertEqual(value['adapter']['id'],'instructions')
        self.assertEqual(presets.recommended(e,self.store),[])
    def test_explicit_config_import_filters_private_settings(self):
        p=self.file('import.ini','[GPU]\nResolutionScale=3\npath=/PRIVATE\n[Accounts]\ntoken=SECRET\n')
        e=Entry('Game',['duckstation'],platform='PlayStation',game_id='SLUS-00875')
        self.assertEqual(profile_capture.read_file(e,p),{'GPU':{'ResolutionScale':3}})
    def test_gtaiv_capture_only_numeric_known_options(self):
        self.file('game/plugins/GTAIV.EFLC.FusionFix.ini','[MAIN]\nFPSLimit=45\nPath=/PRIVATE\nToken=SECRET\n')
        e=Entry('GTA IV',['steam'],platform='Windows',game_id='12210',metadata={'gtaiv_root':str(self.root/'game'),'steam_store':True})
        value=presets.export_current(e,'Test','Alias',self.store)
        self.assertIn('FPSLimit = 45',value['instructions']);self.assertNotIn('/PRIVATE',json.dumps(value));self.assertNotIn('SECRET',json.dumps(value))
    def test_api_publication_is_owned_by_user_and_scoped_to_game(self):
        api=API(self.root/'community.db',client_id='test')
        with api.db() as db:
            for user in ('one','two'):db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest(user),user,user,time.time()+60))
        e=Entry('Port',['port']);value=presets.export_current(e,'Guide','Fake author',self.store)
        response=api.handle('POST','/v1/presets',{},value,'one');query={'game':[value['game']['id'].lower()],'adapter':['instructions']}
        self.assertEqual(response['status'],'pending')
        mine=api.handle('GET','/v1/me/presets',query,{},'one')['presets'];self.assertEqual(mine[0]['author'],'one');self.assertEqual(mine[0]['preset']['author'],'one')
        self.assertEqual(api.handle('GET','/v1/me/presets',query,{},'two')['presets'],[])
        self.assertEqual(api.handle('GET','/v1/presets',query,{})['presets'],[])
        with api.db() as db:db.execute("UPDATE presets SET status='approved'")
        self.assertEqual(len(api.handle('GET','/v1/presets',query,{})['presets']),1)
        query['game']=['different'];self.assertEqual(api.handle('GET','/v1/presets',query,{})['presets'],[])

    def test_custom_runtime_or_instructions_do_not_inherit_bundled_verification(self):
        e=Entry('Mario Kart Wii',['port'],platform='WiiCompiled',game_id='RMCP01')
        value=presets.recommended(e,self.store)[0];self.assertTrue(presets.is_bundled(value))
        value['instructions']='Additional steps';self.assertFalse(presets.is_bundled(value))
        value.pop('instructions');value['runtime']={'kind':'proton','version':'Proton 9.0'};self.assertFalse(presets.is_bundled(value))
