import io,json,pathlib,subprocess,sys,tempfile,threading,time,unittest,zipfile
from unittest.mock import patch
from deck_library import port_packages,ports,port_runtime,project2099,project2099_update,presets
from deck_library.models import Store
from deck_library.setup_wii import run_logged,Cancelled

class PackageTests(unittest.TestCase):
    def test_native_preferred_and_unsupported_architectures_and_installers_excluded(self):
        names=['game-win64.zip','game-linux-aarch64.AppImage','game-linux-x86_64.tar.zst','game-win64-setup.exe']
        self.assertEqual(port_packages.select([{'name':n} for n in names])['asset']['name'],names[2])
        self.assertEqual(port_packages.select([{'name':names[0]}])['runtime'],'proton')
        self.assertEqual(port_packages.select([{'name':'game-win32.zip'}])['runtime'],'proton')
        for name in ('game-windows-arm64.zip','game-win64-installer.exe','game-win64-debug.zip','game-linux-x64.sha256','game-linux-x64.yml'):
            self.assertIsNone(port_packages.select([{'name':name}]),name)

    def test_portable_update_preserves_saves_and_uses_stable_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);store=Store(root/'private');destination=root/'ports';item={'repository':'owner/Game','folderName':'Game'}
            def install(tag,replace=False):
                data=io.BytesIO()
                with zipfile.ZipFile(data,'w') as z:z.writestr('Game/Game.exe',b'MZ'+tag.encode());z.writestr('Game/data.txt','assets')
                release={'tag_name':tag,'assets':[{'name':'Game-win64.zip','browser_download_url':'https://github.com/owner/Game/releases/download/v1/Game-win64.zip'}]}
                if replace:release['assets'].append({'name':'Game-linux-x64.zip','browser_download_url':'https://github.com/owner/Game/releases/download/v2/Game-linux-x64.zip'})
                with patch.object(ports,'download',side_effect=lambda url,path,**kw:path.write_bytes(data.getvalue())),patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')):
                    return ports.install(item,store,destination,get=lambda _:release,progress=lambda _:None,replace=replace)
            record=install('v1');folder=destination/'Game';(folder/'UserData').mkdir();(folder/'UserData/save.bin').write_bytes(b'progress')
            from deck_library.models import atomic_json
            record['inputs']={'rom':str(root/'owned.rom')};atomic_json(store.root/'ports.json',{'owner/Game':record})
            entry=ports.entry_for(folder);self.assertEqual(entry.platform,'Windows');self.assertIn('deck_library.port_runtime',entry.command)
            with patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')):
                first=port_runtime.command_for(folder,store)
                install('v2',True);second=port_runtime.command_for(folder,store)
            self.assertEqual(first[1]['STEAM_COMPAT_DATA_PATH'],second[1]['STEAM_COMPAT_DATA_PATH'])
            self.assertEqual((folder/'UserData/save.bin').read_bytes(),b'progress');self.assertEqual((folder/'Game.exe').read_bytes(),b'MZv2')
            self.assertEqual(ports.entry_for(folder).id,entry.id)
            self.assertEqual(ports.records(store)['owner/Game']['inputs'],record['inputs'])
            backup=next((destination/'.deck-library-replaced').iterdir());self.assertEqual((backup/'Game.exe').read_bytes(),b'MZv1')

    def test_a_zip_that_only_wraps_a_tar_gz_is_opened_and_the_port_shows_in_the_library(self):
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);inner=io.BytesIO()
            with tarfile.open(fileobj=inner,mode='w:gz') as tar:
                info=tarfile.TarInfo('Game');info.size=4;info.mode=0o755;tar.addfile(info,io.BytesIO(b'\x7fELF'))
                info=tarfile.TarInfo('assets/data.txt');info.size=2;tar.addfile(info,io.BytesIO(b'ok'))
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as z:z.writestr('Game.tar.gz',inner.getvalue())
            release={'tag_name':'v1','assets':[{'name':'Game-Linux-X64.zip','browser_download_url':'https://github.com/a/Game/releases/download/v1/Game-Linux-X64.zip'}]}
            store=Store(root/'private')
            with patch.object(ports,'download',side_effect=lambda url,path,**kw:path.write_bytes(data.getvalue())):
                record=ports.install({'repository':'a/Game','folderName':'Game'},store,root/'ports',get=lambda _:release,progress=lambda _:None)
            self.assertEqual(record['executable'],'Game');self.assertFalse((root/'ports/Game/Game.tar.gz').exists());self.assertTrue((root/'ports/Game/assets/data.txt').is_file())
            self.assertIsNotNone(ports.entry_for(root/'ports/Game'))

    def test_a_package_with_several_tools_starts_the_launcher_then_the_plain_binary(self):
        for names,expected in ((['openmw','openmw.x86_64','openmw-launcher','openmw-launcher.x86_64','bsatool','esmtool'],'openmw-launcher'),(['openmw','openmw.x86_64','bsatool'],'openmw'),(['alpha','beta'],'')):
            with tempfile.TemporaryDirectory() as tmp:
                for name in names:(pathlib.Path(tmp)/name).write_bytes(b'\x7fELF')
                if expected=='openmw-launcher':
                    wrapper=pathlib.Path(tmp)/'openmw-launcher';wrapper.write_bytes(b'#!/bin/sh\nexec "$0.x86_64"\n');wrapper.chmod(0o755)
                found=ports.find_executable(tmp,'OpenMW/openmw');self.assertEqual(found.name if found else '',expected)

    def test_unsafe_declared_executable_is_rejected_before_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as z:z.writestr('game',b'\x7fELF')
            release={'assets':[{'name':'game-linux.zip','browser_download_url':'https://github.com/a/b'}]}
            with patch.object(ports,'download',side_effect=lambda url,path,**kw:path.write_bytes(data.getvalue())),self.assertRaisesRegex(ValueError,'sale del paquete'):
                ports.install({'repository':'a/b','exe':'../escape'},Store(root/'private'),root/'ports',get=lambda _:release,progress=lambda _:None)

    def test_windows_runtime_rejects_receipt_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);game=root/'game';game.mkdir();(root/'outside.exe').write_bytes(b'MZ')
            (game/'.deck-library-port.json').write_text(json.dumps({'executable':'../outside.exe','repository':'a/b'}))
            with self.assertRaises(ValueError):port_runtime.command_for(game,Store(root/'private'))

    def test_update_rollback_if_final_move_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);game=root/'ports/game';game.mkdir(parents=True);(game/'game').write_bytes(b'old')
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as z:z.writestr('game',b'\x7fELFnew')
            release={'assets':[{'name':'game-linux.zip','browser_download_url':'https://github.com/a/game'}]}
            with patch.object(ports,'download',side_effect=lambda url,path,**kw:path.write_bytes(data.getvalue())),patch('shutil.move',side_effect=OSError('disk error')),self.assertRaises(OSError):
                ports.install({'repository':'a/game'},Store(root/'private'),root/'ports',get=lambda _:release,progress=lambda _:None,replace=True)
            self.assertEqual((game/'game').read_bytes(),b'old')

    def test_bzip_archive_paths_are_validated(self):
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);archive=root/'game.tar.bz2';target=root/'out';target.mkdir()
            with tarfile.open(archive,'w:bz2') as tar:
                member=tarfile.TarInfo('../escape');member.size=1;tar.addfile(member,io.BytesIO(b'x'))
            with self.assertRaises(ValueError):ports.extract(archive,target)
            self.assertFalse((root/'escape').exists())

class InstallerProcessTests(unittest.TestCase):
    def test_wine_diagnostics_stay_in_log_and_idle_process_is_stopped(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=io.StringIO();messages=[];cleanup=[]
            code="import time;print('wine: using kernel write watches, use_kernel_writewatch 1.',flush=True);time.sleep(20)"
            started=time.monotonic()
            with self.assertRaisesRegex(RuntimeError,'dejó de avanzar'):
                run_logged([sys.executable,'-u','-c',code],tmp,None,log,messages.append,threading.Event(),idle_timeout=.1,cleanup=lambda:cleanup.append(True))
            self.assertLess(time.monotonic()-started,5);self.assertEqual(cleanup,[True]);self.assertIn('kernel write watches',log.getvalue());self.assertFalse(any('kernel write' in m for m in messages))

    def test_cancelled_process_stops_and_retains_useful_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            cancel=threading.Event();messages=[]
            def progress(text):
                messages.append(text)
                if text=='25% Copying':cancel.set()
            with self.assertRaises(Cancelled):run_logged([sys.executable,'-u','-c',"import time;print('25% Copying',flush=True);time.sleep(20)"],tmp,None,io.StringIO(),progress,cancel)
            self.assertIn('25% Copying',messages)

    def test_activity_tracks_staged_bytes_not_wine_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=pathlib.Path(tmp);events=[];poll=project2099_update.installation_activity(work,events.append,interval=0)
            self.assertFalse(poll());stage=work/'game.installing-123';stage.mkdir();(stage/'part').write_bytes(b'data');self.assertTrue(poll());self.assertFalse(poll());(stage/'part').write_bytes(b'more data');self.assertTrue(poll());self.assertIn('GB escritos',events[-1]['text'])

class Beta5Tests(unittest.TestCase):
    def test_new_layout_discovered_and_old_profiles_are_not_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);game=root/'ports/project2099'
            for name in ('Project 2099.exe','Engine/Project2099.exe','Engine/rexruntime.dll'):
                p=game/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'MZ')
            (game/'deck-library-project2099.json').write_text(json.dumps({'version':'2.0.0-beta.5'}))
            entry=project2099.discover(root,{})[0];self.assertEqual(entry.metadata['engine'],'reeot');self.assertTrue(entry.source.endswith('Project 2099.exe'));self.assertEqual(presets.recommended(entry,Store(root/'private')),[])

    def test_installer_prefix_is_separate_from_tested_game_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp)
            with patch.object(project2099,'proton_path',return_value=pathlib.Path('/proton11')):
                _,env=project2099.installer_environment(store)
            self.assertNotEqual(env['STEAM_COMPAT_DATA_PATH'],project2099.proton_env(store,'Proton 9.0 (Beta)')['STEAM_COMPAT_DATA_PATH'])
            self.assertTrue(env['STEAM_COMPAT_DATA_PATH'].endswith('project2099-installer'))

    def test_beta5_migration_uses_installer_runtime_and_preserves_library_identity(self):
        from tests.test_ports_015 import ProjectUpdateTests
        with tempfile.TemporaryDirectory() as tmp:
            store,folder,entry,source,release=ProjectUpdateTests().fixture(pathlib.Path(tmp));identity=entry.id;entry.command+=['--proton','Proton 9.0 (Beta)'];seen=[]
            def runner(command,cwd,env,*args):
                seen.append((command,env));stage=pathlib.Path(command[5][2:].replace('\\','/'))
                for name in ('Project 2099.exe','Engine/Project2099.exe','Engine/rexruntime.dll'):
                    path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'MZ')
            with patch.object(presets,'busy',return_value=False),patch.object(project2099,'proton_path',return_value=pathlib.Path('/proton11')),patch('shutil.disk_usage',return_value=__import__('shutil')._ntuple_diskusage(100<<30,0,100<<30)):
                result=project2099_update.update(entry,source,release,store,runner=runner)
            self.assertEqual(seen[0][0][0],'/proton11');self.assertIn('project2099-installer',seen[0][1]['STEAM_COMPAT_DATA_PATH'])
            current=store.load()[0];self.assertEqual(current.id,identity);self.assertNotIn('--proton',current.command);self.assertEqual(current.metadata['engine'],'reeot');self.assertTrue(current.source.endswith('Project 2099.exe'));self.assertEqual((folder/'UserData/save.bin').read_bytes(),b'save');self.assertTrue(pathlib.Path(result['backup']).is_dir())

    def test_actual_published_package_names_choose_the_deck_build(self):
        samples=[(['Zelda64Recompiled-v1.2.2-Linux-Flatpak-X64.zip','Zelda64Recompiled-v1.2.2-Linux-X64.zip'],'Zelda64Recompiled-v1.2.2-Linux-X64.zip'),(['sm64coopdx_Linux.zip','sm64coopdx_SteamOS.zip','sm64coopdx_Windows.zip'],'sm64coopdx_SteamOS.zip'),(['EdgeOfTimeRecomp-v0.6.7-20261004_1612-win-amd64.zip','EdgeOfTimeRecomp-v0.6.7-20261004_1612-x86_64.AppImage'],'EdgeOfTimeRecomp-v0.6.7-20261004_1612-x86_64.AppImage')]
        for names,expected in samples:self.assertEqual(port_packages.select([{'name':n} for n in names])['asset']['name'],expected)
