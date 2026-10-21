import json,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import ports,port_packages,library_app,service,original_data
from deck_library.models import Store,Entry,atomic_json
from deck_library.runtime import make_launcher
from deck_library.steam import update_shortcuts

class DeckReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'data');self.cfg=self.root/'steam/config'
    def tearDown(self):self.temp.cleanup()
    def install_self_shortcut(self):
        entry=library_app.entry();entry.metadata['steam_appid']=123
        self.store.save([entry]);launcher=make_launcher(entry,self.store)
        update_shortcuts(self.cfg,[entry],lambda _:launcher,is_running=lambda:False)
        return entry
    def test_unchanged_self_shortcut_does_not_create_a_pending_change(self):
        e=self.install_self_shortcut()
        with patch.object(service,'steam_running',return_value=True):result=service.queue_entries([library_app.entry()],self.cfg,self.store,start_worker=False)
        self.assertEqual(result['state'],'idle');self.assertFalse((self.store.root/'pending.json').exists());self.assertEqual(self.store.load()[0].metadata['steam_appid'],123)
    def test_reconcile_only_removes_a_redundant_self_update(self):
        e=self.install_self_shortcut();other=Entry('Other',['other']);self.store.save([e,other])
        atomic_json(self.store.root/'pending.json',{'account':str(self.cfg),'ids':[e.id,other.id],'controllers':[42]})
        self.assertEqual(service.reconcile_pending(self.store),1)
        pending=json.loads((self.store.root/'pending.json').read_text());self.assertEqual(pending['ids'],[other.id]);self.assertEqual(pending['controllers'],[42])
        e.icon='new-icon.png';self.store.save([e,other]);pending['ids']=[e.id];atomic_json(self.store.root/'pending.json',pending)
        self.assertEqual(service.reconcile_pending(self.store),0)
    def test_reconcile_removes_the_empty_queue_without_touching_steam(self):
        e=self.install_self_shortcut();path=self.cfg/'shortcuts.vdf';before=path.read_bytes()
        atomic_json(self.store.root/'pending.json',{'account':str(self.cfg),'ids':[e.id]})
        self.assertEqual(service.reconcile_pending(self.store),1);self.assertFalse((self.store.root/'pending.json').exists());self.assertEqual(path.read_bytes(),before)
    def test_unlabelled_packages_are_detected_from_contents_and_tools_are_ignored(self):
        self.assertEqual(port_packages.select([{'name':'BLACK-XBERecomp.zip'}])['runtime'],'detect')
        (self.root/'tools').mkdir();(self.root/'tools/compiler.exe').write_bytes(b'MZtool')
        with self.assertRaises(ValueError):port_packages.detect_runtime(self.root)
        (self.root/'game.exe').write_bytes(b'MZgame');self.assertEqual(port_packages.detect_runtime(self.root),'proton')
        (self.root/'game').write_bytes(b'\x7fELFgame');self.assertEqual(port_packages.detect_runtime(self.root),'linux')
    def test_bayonetta_prefers_available_native_builder(self):
        windows={'tag_name':'v1','assets':[{'name':'B2recomp-builder.zip'}]};linux={'tag_name':'linux-test','assets':[{'name':'B2recomp-linux-builder.zip'}]}
        release=ports.release_for('K0NL/B2recomp',get=lambda url:[windows,linux])
        self.assertEqual(release,linux);item=ports.clean({'repository':'K0NL/B2recomp'})
        self.assertEqual(ports.package_plan(item,linux['assets'])['runtime'],'linux');self.assertEqual(item['exe'],'B2recomp')
    def test_reviewed_black_packages_and_source_only_status(self):
        for repo,name in (('TGP482/BLACK-XBERecomp','BLACK-XBERecomp.zip'),('euspring1/BlackDefinitiveHDPC','BlackDefinitiveHDPCv1.3.zip')):
            item=ports.clean({'repository':repo});self.assertEqual(ports.package_plan(item,[{'name':name}])['runtime'],'proton');self.assertEqual(item['setup'],'original_data')
        self.assertIsNone(ports.package_plan(ports.clean({'repository':'TheNIKITO/LittleBigPlanet-3---PC'}),[{'name':'source.zip'}]))
    def test_original_selection_prepares_assets_preserving_the_original(self):
        folder=self.root/'ports/BLACK';folder.mkdir(parents=True);source=self.root/'Black.iso';source.write_bytes(b'own image')
        record={'repository':'TGP482/BLACK-XBERecomp','folder':'BLACK','setup':'original_data','original_data':{'destination':'assets','iso':True},'executable':'BLACK.exe'}
        atomic_json(self.store.root/'ports.json',{record['repository']:record})
        self.assertFalse(ports.requirements(record,[])[0][0]);ports.set_input(record['repository'],'original_data',source,self.store)
        with patch.object(ports,'ports_root',return_value=self.root/'ports'):result=ports.configure(record['repository'],self.store,progress=lambda _:None)
        self.assertTrue(result['configured']);self.assertEqual((folder/'assets/Black.iso').read_bytes(),source.read_bytes());self.assertEqual(source.read_bytes(),b'own image')
    def test_original_copy_refuses_links_and_conflicting_files(self):
        folder=self.root/'port';folder.mkdir();source=self.root/'game';source.mkdir();(source/'default.xbe').write_bytes(b'XBEHown')
        (source/'link').symlink_to(self.root/'elsewhere')
        with self.assertRaises(ValueError):original_data.prepare(folder,source,{'destination':'assets'})
        (source/'link').unlink();(folder/'assets').mkdir();(folder/'assets/default.xbe').write_bytes(b'existing')
        with self.assertRaises(ValueError):original_data.prepare(folder,source,{'destination':'assets'})
        self.assertEqual((folder/'assets/default.xbe').read_bytes(),b'existing')
    def test_builder_update_keeps_settings_and_saves_but_rebuilds_code(self):
        old=self.root/'old';new=self.root/'new';(old/'build-linux/play/userdata').mkdir(parents=True);new.mkdir()
        (old/'build-linux/play/userdata/save.dat').write_text('save');(old/'config').mkdir();(old/'config/graphics.ini').write_text('settings')
        (old/'build-linux/game_native').write_bytes(b'old executable')
        item=ports.clean({'repository':'K0NL/B2recomp'});port_packages.preserve_saves(old,new,extra=item['preserve'])
        self.assertEqual((new/'build-linux/play/userdata/save.dat').read_text(),'save');self.assertEqual((new/'config/graphics.ini').read_text(),'settings')
        self.assertFalse((new/'build-linux/game_native').exists())

    def test_bayonetta_uses_its_direct_play_script_after_building(self):
        folder=self.root/'B2recomp';folder.mkdir();(folder/'B2recomp').write_text('#!/bin/sh\n')
        atomic_json(folder/'.deck-library-port.json',{'repository':'K0NL/B2recomp','name':'Bayonetta 2','folder':'B2recomp','runtime':'linux','executable':'B2recomp','setup':'','args':[]})
        self.assertEqual(ports.entry_for(folder).command[0],str(folder/'B2recomp'))
        (folder/'scripts').mkdir();(folder/'scripts/play.sh').write_text('#!/bin/sh\n');(folder/'build-linux').mkdir();(folder/'build-linux/game_native').write_bytes(b'\x7fELF')
        self.assertEqual(ports.entry_for(folder).command[0],str(folder/'scripts/play.sh'))

    def test_7z_listing_rejects_escaping_paths_before_extracting(self):
        from deck_library import archive7z
        from types import SimpleNamespace
        with patch.object(archive7z.shutil,'which',return_value='7z'),patch.object(archive7z.subprocess,'run',return_value=SimpleNamespace(stdout='Path = ../outside\nFolder = -\n')) as run:
            with self.assertRaises(ValueError):archive7z.extract(self.root/'game.7z',self.root/'output')
        self.assertEqual(run.call_count,1);self.assertFalse((self.root/'outside').exists())

    def test_real_7z_portable_package_roundtrip(self):
        import shutil,subprocess
        tool=shutil.which('7z') or shutil.which('7zz')
        if not tool:self.skipTest('7-Zip not installed')
        source=self.root/'source';source.mkdir();(source/'game.exe').write_bytes(b'MZgame');archive=self.root/'Game.7z'
        subprocess.run([tool,'a',str(archive),'game.exe'],cwd=source,capture_output=True,check=True)
        destination=self.root/'output';destination.mkdir();ports.extract(archive,destination)
        self.assertEqual((destination/'game.exe').read_bytes(),b'MZgame');self.assertEqual(port_packages.detect_runtime(destination),'proton')
        self.assertEqual(port_packages.select([{'name':'Game-Windows-x64.7z'}])['kind'],'archive')
        self.assertEqual(port_packages.select([{'name':'Game-Linux-x64.7z'}])['runtime'],'linux')

    def test_bayonetta_integrated_build_uses_dump_and_versioned_bundled_python(self):
        folder=self.root/'ports/B2recomp';(folder/'deps/python/bin').mkdir(parents=True);(folder/'scripts').mkdir()
        (folder/'deps/python/bin/python3.13').write_bytes(b'\x7fELF');(folder/'scripts/setup.py').write_text('')
        source=self.root/'dump';(source/'exefs').mkdir(parents=True);(source/'exefs/main').write_bytes(b'NSO0');(source/'romfs').mkdir()
        record={**ports.clean({'repository':'K0NL/B2recomp'}),'executable':'B2recomp','runtime':'linux'}
        atomic_json(self.store.root/'ports.json',{record['repository']:record});ports.set_input(record['repository'],'original_data',source,self.store)
        calls=[]
        def run(command,**kwargs):
            calls.append((command,kwargs));(folder/'build-linux').mkdir();(folder/'build-linux/game_native').write_bytes(b'\x7fELF')
        with patch.object(ports,'ports_root',return_value=self.root/'ports'):result=ports.configure(record['repository'],self.store,run=run,progress=lambda _:None)
        self.assertTrue(result['configured']);command,options=calls[0];self.assertTrue(command[0].endswith('python3.13'));self.assertIn(str(source),command);self.assertFalse(options['sandbox']);self.assertLessEqual(int(command[-1]),4)
        self.assertEqual((source/'exefs/main').read_bytes(),b'NSO0')

    def test_bayonetta_cancellation_does_not_mark_the_build_ready(self):
        import threading
        folder=self.root/'ports/B2recomp';(folder/'deps/python/bin').mkdir(parents=True);(folder/'scripts').mkdir()
        (folder/'deps/python/bin/python3').write_bytes(b'\x7fELF');(folder/'scripts/setup.py').write_text('')
        source=self.root/'dump';(source/'exefs').mkdir(parents=True);(source/'exefs/main').write_bytes(b'NSO0');(source/'romfs').mkdir()
        record={**ports.clean({'repository':'K0NL/B2recomp'}),'executable':'B2recomp','runtime':'linux'}
        atomic_json(self.store.root/'ports.json',{record['repository']:record});ports.set_input(record['repository'],'original_data',source,self.store)
        cancelled=threading.Event()
        def run(command,**kwargs):cancelled.set();self.assertTrue(kwargs['until']())
        with patch.object(ports,'ports_root',return_value=self.root/'ports'),self.assertRaises(ports.Cancelled):ports.configure(record['repository'],self.store,run=run,progress=lambda _:None,cancel=cancelled)
        self.assertFalse(ports.records(self.store)[record['repository']].get('configured',False))
