import json,pathlib,shutil,struct,tempfile,threading,unittest,zipfile
from unittest.mock import patch
from deck_library import dante,ports,port_packages
from deck_library.models import Store,atomic_json

def xex(path,title=dante.TITLE_ID):
    data=bytearray(128);data[:4]=b'XEX2';struct.pack_into('>I',data,20,1);struct.pack_into('>II',data,24,0x40006,64);struct.pack_into('>I',data,76,title);path.write_bytes(data)

class DanteSavageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'data')
    def tearDown(self):self.temp.cleanup()
    def test_native_release_skips_newer_windows_and_arm_only_and_respects_proton(self):
        windows={'tag_name':'new','assets':[{'name':'SavageWind-windows.zip'}]}
        arm={'tag_name':'arm','assets':[{'name':'Savage_Wind-aarch64.AppImage'}]}
        linux={'tag_name':'native','assets':[{'name':'Savage_Wind-x86_64.AppImage'},{'name':'SavageWind-windows.zip'}]}
        calls=[]
        def get(url):calls.append(url);return [windows,arm,linux] if '?per_page=20' in url else windows
        item=ports.clean({'repository':'Revivedx/SavageWindRecomp'})
        release=ports.release_for(item['repository'],get)
        self.assertEqual(release,linux);self.assertEqual(ports.package_plan(item,release['assets'])['asset']['name'],'Savage_Wind-x86_64.AppImage')
        calls.clear();self.assertEqual(ports.release_for(item['repository'],get,runtime='proton'),windows);self.assertTrue(calls[0].endswith('/latest'))
    def test_dante_installs_the_motor_among_multiple_executables_and_waits_for_originals(self):
        archive=self.root/'portable.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for name in ('dantes_inferno.exe','DantesInfernoLauncher.exe','extract-xiso.exe'):z.writestr(name,b'MZfixture')
            z.writestr('game/default.xexp',b'new patch')
        release={'tag_name':'test','assets':[{'name':archive.name,'browser_download_url':'https://example.org/game.zip'}]}
        with patch.object(ports,'download',side_effect=lambda url,dest,**kw:shutil.copy2(archive,dest)),patch('deck_library.project2099.proton_path',return_value='/test/proton'):
            record=ports.install({'repository':'florinp93/hells-gate-recomp'},self.store,root=self.root/'ports',get=lambda _:release,progress=lambda _:None)
        self.assertEqual(record['executable'],'dantes_inferno.exe');self.assertEqual(record['runtime'],'proton');self.assertEqual(record['setup'],'dante')
        self.assertFalse(ports.entry_for(self.root/'ports'/record['folder']).metadata['configured']);self.assertFalse(ports.requirements(record,[],self.root)[0][0])
    def test_savage_auto_update_selects_native_even_after_a_windows_install(self):
        item=ports.clean({'repository':'Revivedx/SavageWindRecomp'});folder=self.root/'ports'/item['folder'];folder.mkdir(parents=True);(folder/'old.exe').write_bytes(b'MZ')
        atomic_json(self.store.root/'ports.json',{item['repository']:{'runtime':'proton'}})
        release={'tag_name':'native','assets':[{'name':'Savage_Wind-x86_64.AppImage','browser_download_url':'https://example.org/native'}]}
        with patch.object(ports,'release_for',return_value=release) as get,patch.object(ports,'download',side_effect=lambda url,dest,**kw:dest.write_bytes(b'\x7fELFfixture')):
            record=ports.install(item,self.store,root=self.root/'ports',replace=True,progress=lambda _:None)
        self.assertEqual(get.call_args.kwargs['runtime'],'auto');self.assertEqual(record['runtime'],'linux');self.assertEqual(record['args'],['--appimage-extract-and-run'])
    def test_savage_windows_choice_identifies_game_and_zeldaret_is_not_installable(self):
        item=ports.clean({'repository':'Revivedx/SavageWindRecomp'});self.assertEqual(item['windows_exe'],'savagewind.exe')
        self.assertEqual(ports.package_plan(item,[{'name':'SavageWind-windows.zip'}],runtime='proton')['runtime'],'proton')
        self.assertIsNone(ports.package_plan(ports.clean({'repository':'zeldaret/botw'}),[{'name':'source.zip'}]))
    def original(self,name='original',title=dante.TITLE_ID):
        folder=self.root/name;folder.mkdir();xex(folder/'default.xex',title);(folder/'asset.bin').write_bytes(b'owned fixture');return folder
    def record(self):
        item=ports.clean({'repository':'florinp93/hells-gate-recomp'});folder=self.root/'ports'/item['folder'];folder.mkdir(parents=True);(folder/'dantes_inferno.exe').write_bytes(b'MZfixture');(folder/'extract-xiso.exe').write_bytes(b'MZfixture');(folder/'game').mkdir();(folder/'game/default.xexp').write_bytes(b'published patch')
        record={**item,'runtime':'proton','executable':'dantes_inferno.exe'};atomic_json(self.store.root/'ports.json',{item['repository']:record});atomic_json(folder/'.deck-library-port.json',record);return record,folder
    def test_folder_identity_and_ambiguity_control_auto_detection(self):
        record,folder=self.record();a=self.original();other=self.original('wrong',0x12345678)
        self.assertEqual(dante.find_source(record,[('Other',str(other)),('Dante',str(a))],self.root),str(a))
        b=self.original('second');self.assertEqual(dante.find_source(record,[('a',str(a)),('b',str(b))],self.root),'')
        self.assertIsNone(dante.title_id(other/'asset.bin'))
        with self.assertRaises(ValueError):dante.validate(other)
    def test_folder_configuration_keeps_published_patch_and_original_and_is_reusable(self):
        record,folder=self.record();source=self.original();(source/'default.xexp').write_bytes(b'old patch')
        ports.set_input(record['repository'],'original_data',source,self.store)
        done=ports.configure(record['repository'],self.store,home=self.root,progress=lambda _:None)
        self.assertTrue(done['configured']);self.assertEqual((folder/'game/default.xexp').read_bytes(),b'published patch');self.assertEqual((source/'default.xexp').read_bytes(),b'old patch')
        self.assertIn('--game_data_root=game',done['args']);self.assertIn('--input_backend=sdl',done['args'])
        shutil.rmtree(source)
        self.assertTrue(ports.requirements(done,[],self.root)[0][0]);ports.configure(record['repository'],self.store,home=self.root,progress=lambda _:None)
    def iso(self):
        iso=self.root/'Dante.iso'
        with iso.open('wb') as file:file.seek(32*2048);file.write(b'MICROSOFT*XBOX*MEDIA')
        return iso
    def test_iso_extraction_uses_bundled_tool_and_checks_title_before_promotion(self):
        record,folder=self.record();iso=self.iso();ports.set_input(record['repository'],'original_data',iso,self.store);calls=[]
        def run(command,**kw):
            calls.append((command,kw));target=pathlib.Path(command[command.index('-d')+1][2:].replace('\\','/'));target.mkdir();xex(target/'default.xex');(target/'data.bin').write_bytes(b'data')
        with patch('deck_library.port_runtime.command_for',return_value=(['/proton','run',str(folder/'dantes_inferno.exe')],{'PREFIX':'isolated'})):
            done=ports.configure(record['repository'],self.store,home=self.root,run=run,progress=lambda _:None)
        self.assertTrue(done['configured']);command,options=calls[0];self.assertEqual(pathlib.Path(command[2]).name,'extract-xiso.exe');self.assertEqual(options['env'],{'PREFIX':'isolated'});self.assertEqual((folder/'game/data.bin').read_bytes(),b'data');self.assertTrue(iso.exists())
    def test_wrong_disc_or_cancelled_extraction_keeps_existing_data(self):
        record,folder=self.record();iso=self.iso();cancel=threading.Event()
        for cancelled in (False,True):
            def run(command,**kw):
                target=pathlib.Path(command[command.index('-d')+1][2:].replace('\\','/'));target.mkdir();xex(target/'default.xex',0x12345678)
                if cancelled:cancel.set()
            with patch('deck_library.port_runtime.command_for',return_value=(['/proton','run','game.exe'],{})),self.assertRaises((ValueError,ports.Cancelled)):
                dante.prepare(folder,iso,record['original_data'],self.store,lambda _:None,run,cancel)
            self.assertEqual((folder/'game/default.xexp').read_bytes(),b'published patch');self.assertFalse((folder/'game/default.xex').exists())
            self.assertFalse(list(folder.glob('.dante-data-*')))
    def test_update_preserves_game_and_saves_but_uses_new_title_update(self):
        old=self.root/'old';new=self.root/'new';(old/'game').mkdir(parents=True);(new/'game').mkdir(parents=True)
        (old/'game/default.xex').write_bytes(b'original');(old/'game/default.xexp').write_bytes(b'old patch');(new/'game/default.xexp').write_bytes(b'new patch');(old/'userdata').mkdir();(old/'userdata/save').write_bytes(b'save')
        recipe=ports.clean({'repository':'florinp93/hells-gate-recomp'})
        port_packages.preserve_saves(old,new,extra=recipe['preserve'],exclude=('game/default.xexp',))
        self.assertEqual((new/'game/default.xex').read_bytes(),b'original');self.assertEqual((new/'game/default.xexp').read_bytes(),b'new patch');self.assertEqual((new/'userdata/save').read_bytes(),b'save')
    def test_ps3_and_links_are_rejected_without_replacing_data(self):
        image=self.root/'PS3.iso'
        with image.open('wb') as f:f.seek(0x8000);f.write(b'PS3VOLUME')
        with self.assertRaisesRegex(ValueError,'PS3'):dante.validate(image)
        record,folder=self.record();original=self.original();(original/'link').symlink_to(self.root/'elsewhere')
        with self.assertRaises(ValueError):dante.prepare(folder,original,record['original_data'],self.store,lambda _:None,None)
        self.assertEqual((folder/'game/default.xexp').read_bytes(),b'published patch')
    def test_direct_motor_reads_existing_launcher_settings_without_running_commands(self):
        config=self.root/'dantes_inferno.toml';config.write_text('fullscreen = False\nsmaa = True\nframe_rate = 120\nrender_resolution = "1920x1080"\ninput_backend = "sdl"\nrenderer_override = "xenos"\nuser_language = 5\ngame_data_root = "/other"\n')
        args=dante.arguments(self.root)
        for option in ('--fullscreen=false','--dante_smaa=true','--video_mode_refresh_rate=120','--dante_resolution=1920x1080','--renderer=xenos','--user_language=5','--game_data_root=game'):self.assertIn(option,args)
        self.assertNotIn('--game_data_root=/other',args)
        config.write_text('frame_rate = "120 --help"\ninput_backend = "$(whoami)"\nrender_resolution = "90000x90000"\n')
        args=dante.arguments(self.root);self.assertIn('--input_backend=sdl',args);self.assertFalse(any('whoami' in a or '--help' in a or '90000' in a for a in args))
    def test_cancel_stops_an_extractor_that_produces_no_output(self):
        import os,sys,time
        cancel=threading.Event();timer=threading.Timer(.15,cancel.set);timer.start();start=time.monotonic()
        try:
            with self.assertRaises(ports.Cancelled):dante.run_extractor([sys.executable,'-c','import time;time.sleep(30)'],cwd=self.root,env=dict(os.environ),progress=lambda _:None,log=self.root/'silent.log',cancel=cancel)
        finally:timer.cancel()
        self.assertLess(time.monotonic()-start,5)
