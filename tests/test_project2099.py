import io,json,pathlib,tempfile,tomllib,unittest,zipfile,shutil,subprocess
from unittest.mock import patch
from deck_library import presets,project2099
from deck_library.models import Store

class Project2099Tests(unittest.TestCase):
    def test_ps3_iso_and_zipped_iso_rejected_before_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);iso=root/'game.iso';data=bytearray(0x8100);data[0x8000:0x804e]=b'\x01CD001'+b' '*34+b'PS3VOLUME'+b' '*29;iso.write_bytes(data)
            archive=root/'game.zip'
            with zipfile.ZipFile(archive,'w') as z:z.write(iso,'game.iso')
            with patch('urllib.request.urlretrieve') as download:
                for source in (iso,archive):
                    with self.assertRaisesRegex(ValueError,'PlayStation 3'):
                        project2099.prepare(source,root/'install',Store(root/'data'))
                download.assert_not_called();self.assertFalse((root/'install').exists())
    def test_xbox_header_is_only_precheck(self):
        data=bytearray(65536+100);data[65536:65554]=b'MICROSOFT*XBOX*MEDIA'
        project2099.check_image(io.BytesIO(data))
        with self.assertRaises(ValueError):project2099.check_image(io.BytesIO(b'invalid'))
    def test_preset_preserves_paths_language_and_save_settings_and_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);config=root/'spider_man_edge_of_time.toml';original="user_language=5\ngame_data_root='Data/Original'\ncache_path='/PRIVATE/cache'\nwindow_width=1920\n[other]\nwindow_width=333\n";config.write_text(original)
            entry=project2099.entry_for(root,project2099.VERSION);store=Store(root/'private');profile=json.loads((pathlib.Path(__file__).resolve().parents[1]/'presets/project2099-deck-720p60.json').read_text())
            with patch('deck_library.presets.emulator_busy',return_value=False):presets.apply(entry,profile,store)
            value=tomllib.loads(config.read_text());self.assertEqual(value['user_language'],5);self.assertEqual(value['window_width'],1280);self.assertEqual(value['other']['window_width'],333)
            export=presets.export_current(entry,'Test','Alias',store);self.assertNotIn('/PRIVATE',json.dumps(export));self.assertEqual(export['settings']['runtime']['genry_eot_target_fps'],60)
            presets.restore(entry,store);self.assertEqual(config.read_text(),original)
    def test_does_not_discover_setup_or_incomplete_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);folder=root/'ports/project2099';folder.mkdir(parents=True)
            (folder/'SpiderManEOT.exe').touch();self.assertEqual(project2099.discover(root,{}),[])
            for name in ('rexruntime.dll','spider_man_edge_of_time.toml'):(folder/name).touch()
            result=project2099.discover(root,{});self.assertEqual(len(result),1);self.assertEqual(result[0].metadata['adapter'],'project2099')

    @unittest.skipUnless(shutil.which('7z'), '7-Zip is optional')
    def test_7z_ps3_rejected_before_download_and_ambiguous_images_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);iso=root/'game.iso';data=bytearray(0x8100);data[0x8030:0x8039]=b'PS3VOLUME';iso.write_bytes(data)
            archive=root/'game.7z'
            subprocess.run(['7z','a',str(archive),str(iso)],check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(project2099.sevenzip_image(archive)[2],len(data))
            with patch('urllib.request.urlretrieve') as download:
                with self.assertRaisesRegex(ValueError,'PlayStation 3'):project2099.prepare(archive,root/'install',Store(root/'data'))
                download.assert_not_called()
            second=root/'second.iso';second.write_bytes(data)
            subprocess.run(['7z','a',str(archive),str(second)],check=True,stdout=subprocess.DEVNULL)
            with self.assertRaisesRegex(ValueError,'una sola ISO'):project2099.validate_source(archive)

    def test_rejects_apply_when_wine_process_name_is_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);config=root/'spider_man_edge_of_time.toml';config.write_text('user_language=5\n')
            entry=project2099.entry_for(root,project2099.VERSION);store=Store(root/'data')
            profile=next(p for p in presets.catalog(store) if p['id']=='project2099-deck-1080p-performance')
            with patch('deck_library.presets.emulator_busy',side_effect=lambda name:name=='SpiderManEOT.exe'[:15]):
                with self.assertRaisesRegex(RuntimeError,'debe estar cerrado'):presets.apply(entry,profile,store)
            self.assertEqual(config.read_text(),'user_language=5\n');self.assertFalse((store.root/'preset-backups').exists())

    def test_explicit_proton_uses_separate_prefix_and_rejects_unknown_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);store=Store(root/'private')
            for name in ('Proton 10.0','Proton 11.0'):
                p=root/'.local/share/Steam/steamapps/common'/name/'proton';p.parent.mkdir(parents=True);p.touch()
            self.assertEqual(project2099.proton_path(root).parent.name,'Proton 11.0')
            self.assertEqual(project2099.proton_path(root,'Proton 10.0').parent.name,'Proton 10.0')
            self.assertNotEqual(project2099.proton_env(store)['STEAM_COMPAT_DATA_PATH'],project2099.proton_env(store,'Proton 10.0')['STEAM_COMPAT_DATA_PATH'])
            with self.assertRaises(ValueError):project2099.proton_path(root,'../../external')

    def test_beta5_launches_engine_directly_with_installed_data_and_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)/'Game folder'
            for name in ('Project 2099.exe','Engine/Project2099.exe','Engine/rexruntime.dll','Data/Original/Default.xex'):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'file')
            receipt=root/'Support/Install/INSTALL_RECEIPT.json';receipt.parent.mkdir(parents=True);receipt.write_text(json.dumps({'EffectiveLanguage':5}))
            with patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')),patch.object(project2099,'proton_env',return_value={}):
                command,cwd,env=project2099.launch_plan(root/'SpiderManEOT.exe')
                self.assertEqual(command[2],str(root/'Engine/Project2099.exe'));self.assertEqual(cwd,root)
                self.assertIn('--game_data_root=Z:'+str(root/'Data/Original').replace('/','\\'),command);self.assertIn('--eot_language=es',command);self.assertIn('--profile=default',command)
                launcher,_,_=project2099.launch_plan(root/'SpiderManEOT.exe',launcher=True)
                self.assertEqual(launcher[2],str(root/'Project 2099.exe'));self.assertEqual(len(launcher),3)
                receipt.write_text(json.dumps({'EffectiveLanguage':1}));command,_,_=project2099.launch_plan(root/'Engine/Project2099.exe');self.assertIn('--eot_language=en',command)

    def test_legacy_direct_launch_retains_explicit_proton_and_missing_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'SpiderManEOT.exe').touch();(root/'rexruntime.dll').touch()
            with patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')) as runtime,patch.object(project2099,'proton_env',return_value={}):
                command,_,_=project2099.launch_plan(root/'SpiderManEOT.exe','Proton 9.0 (Beta)');self.assertEqual(command[2],str(root/'SpiderManEOT.exe'));runtime.assert_called_with(preferred='Proton 9.0 (Beta)')
                for name in ('Project 2099.exe','Engine/Project2099.exe','Engine/rexruntime.dll'):
                    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
                with self.assertRaisesRegex(ValueError,'datos instalados'):project2099.launch_plan(root/'SpiderManEOT.exe')
