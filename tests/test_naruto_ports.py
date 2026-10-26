import io,pathlib,struct,tempfile,threading,unittest,zipfile
from unittest.mock import patch
from deck_library import original_data,ports,port_packages,port_runtime,project2099
from deck_library.models import Store
from deck_library.ports import Cancelled

BROKEN='jorjbarbosa/broken-bond-recomp'
OTHER='Auremana666/Naruto-The-Broken-Bond-PC-Port'

def xex(path,title=0x55530825):
    data=bytearray(128);data[:4]=b'XEX2';struct.pack_into('>I',data,20,1);struct.pack_into('>II',data,24,0x40006,64);struct.pack_into('>I',data,76,title);path.write_bytes(data)

class NarutoPortsTests(unittest.TestCase):
    def test_cached_catalog_rows_receive_new_recipes_without_a_network_refresh(self):
        repo='jorjbarbosa/naruto-rise-recomp'
        item=next(i for i in ports.merged([{'repository':repo,'name':'Naruto','ai':True,'source':'Quiver'}]) if i['repository']==repo)
        self.assertEqual(item['setup'],'original_data');self.assertEqual(item['supported_os'],['windows']);self.assertTrue(item['ai']);self.assertEqual(item['source'],'Quiver')
        for repo in (BROKEN,OTHER):self.assertLessEqual(ports.compatibility({'repository':repo})['score'],50)

    def test_portable_launcher_engine_pairs_are_selected_without_guessing_other_games(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            for name in ('broken_bond.exe','broken_bond_launcher.exe'):(root/name).write_bytes(b'MZtest')
            self.assertEqual(port_packages.windows_executable(root,'unrelated/project').name,'broken_bond_launcher.exe')
            (root/'another_game.exe').write_bytes(b'MZtest');self.assertFalse(port_packages.windows_executable(root,'unrelated/project'))

    def test_both_broken_bond_packages_install_through_proton_and_update_without_losing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);store=Store(root/'private')
            for repo,names in ((BROKEN,['broken_bond.exe','broken_bond_launcher.exe']),(OTHER,['Naruto The Broken Bond PC.exe'])):
                item=ports.clean({'repository':repo});payload=io.BytesIO()
                with zipfile.ZipFile(payload,'w') as z:
                    for name in names:z.writestr('package/'+name,b'MZfixture')
                release={'tag_name':'v2','assets':[{'name':'Naruto.zip','browser_download_url':'https://github.com/'+repo+'/asset.zip'}]}
                with patch.object(ports,'download',side_effect=lambda _,target,**kw:target.write_bytes(payload.getvalue())),patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')):
                    record=ports.install(item,store,root/'ports',get=lambda _:release,progress=lambda _:None)
                    self.assertEqual(record['runtime'],'proton');self.assertEqual(record['executable'],item['windows_exe'])
                    folder=root/'ports'/item['folder'];entry=ports.entry_for(folder)
                    self.assertIn('deck_library.port_runtime',entry.command);self.assertFalse(entry.metadata['configured'])
                    if repo==OTHER:
                        iso=root/'owned.iso';data=bytearray(65636);data[65536:65554]=b'MICROSOFT*XBOX*MEDIA';iso.write_bytes(data)
                        ports.set_input(repo,'original_data',iso,store);ports.configure(repo,store,home=root,progress=lambda _:None);iso.unlink()
                    save=folder/('user' if repo==BROKEN else 'hdd')/'save.dat';save.parent.mkdir();save.write_bytes(b'progress')
                    config=folder/('broken_bond.toml' if repo==BROKEN else 'naruto.toml');config.write_text('custom = true')
                    record=ports.install({**item,'folderName':'Renamed catalog folder'},store,root/'ports',get=lambda _:release,replace=True,progress=lambda _:None)
                    self.assertEqual(record['folder'],item['folder']);self.assertFalse((root/'ports/Renamed catalog folder').exists())
                    self.assertEqual(save.read_bytes(),b'progress');self.assertEqual(config.read_text(),'custom = true')
                    if repo==OTHER:
                        self.assertTrue(ports.requirements(record,[],home=root)[0][0]);ports.configure(repo,store,home=root,progress=lambda _:None)
                    command,env=port_runtime.command_for(folder,store);self.assertEqual(command[:2],['/fake/proton','run'])
                    self.assertIn(ports.port_id(repo),env['STEAM_COMPAT_DATA_PATH'])

    def test_extracted_originals_are_matched_by_title_and_revision_and_never_overwrite_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);source=root/'original';source.mkdir();xex(source/'default.xex');(source/'data').write_text('original')
            spec={'kind':'xbox360','destination':'game','title_id':'55530825','sha256':[ports.sha256_file(source/'default.xex')]}
            record={'folder':'Naruto','original_data':spec}
            self.assertEqual(original_data.find_source(record,[('Wrong name',str(source))],root),str(source))
            second=root/'another';second.mkdir();xex(second/'default.xex')
            self.assertEqual(original_data.find_source(record,[('a',str(source)),('b',str(second))],root),'')
            with self.assertRaisesRegex(ValueError,'revisión'):original_data.validate(source,{**spec,'sha256':['0'*64]})
            xex(second/'default.xex',0x12345678)
            with self.assertRaises(ValueError):original_data.validate(second,spec)
            folder=root/'ports/Naruto';folder.mkdir(parents=True);original_data.prepare(folder,source,spec,lambda _:None)
            self.assertEqual((folder/'game/data').read_text(),'original')
            (folder/'game/data').write_text('different')
            with self.assertRaisesRegex(ValueError,'otro archivo'):original_data.prepare(folder,source,spec,lambda _:None)
            self.assertEqual((source/'data').read_text(),'original')
            source.rename(root/'removed')
            self.assertEqual(original_data.find_source(record,[],root),str(folder/'game'))

    def test_iso_selection_rejects_wrong_containers_and_reuses_the_managed_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);folder=root/'ports/Naruto';folder.mkdir(parents=True);iso=root/'own.iso'
            data=bytearray(65636);data[65536:65554]=b'MICROSOFT*XBOX*MEDIA';iso.write_bytes(data)
            spec=ports.clean({'repository':OTHER})['original_data']
            self.assertEqual(original_data.validate(iso,spec),iso)
            original_data.prepare(folder,iso,spec,lambda _:None)
            self.assertEqual((folder/'assets/own.iso').read_bytes(),data)
            record={'folder':'Naruto','original_data':spec,'configured':True,'configured_with':'own.iso','inputs':{'original_data':str(iso)}}
            iso.unlink();self.assertEqual(original_data.find_source(record,[],root),str(folder/'assets/own.iso'))
            wrong=root/'ps3.iso';data[32768:32777]=b'PS3VOLUME';wrong.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'PlayStation 3'):original_data.validate(wrong,spec)
            cancel=threading.Event();cancel.set()
            with self.assertRaises(Cancelled):original_data.prepare(root/'new',folder/'assets/own.iso',spec,cancel=cancel)

    def test_windows_archives_platforms_and_asset_prefix_apply_to_proton_too(self):
        self.assertEqual(port_packages.select([{'name':'game-win64.tar.gz'}])['kind'],'archive')
        for name in ('game-3DS.zip','game-PSP.zip','game-Switch.zip','game-notices.zip','game-web-data.zip'):
            self.assertIsNone(port_packages.select([{'name':name}],runtime='proton'),name)
        choices=[{'name':'Other-win64.zip'},{'name':'Game-win64.tar.xz'}]
        self.assertEqual(port_packages.select(choices,asset_prefix='Game-')['asset']['name'],'Game-win64.tar.xz')
        choices=[{'name':'game-3DS.zip'},{'name':'game-MinGW-X86_64.zip'}]
        self.assertEqual(port_packages.select(choices)['asset']['name'],'game-MinGW-X86_64.zip')

    def test_proton_is_found_on_external_storage_and_ge_is_a_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=pathlib.Path(tmp);steam=home/'.local/share/Steam';(steam/'steamapps').mkdir(parents=True)
            external=home/'SD Card';tool=external/'steamapps/common/Proton 11.0/proton';tool.parent.mkdir(parents=True);tool.write_text('proton')
            (steam/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "1" { "path" "'+str(external)+'" } }')
            self.assertEqual(project2099.proton_path(home),tool)
            tool.unlink();ge=steam/'compatibilitytools.d/GE-Proton10-26/proton';ge.parent.mkdir(parents=True);ge.write_text('proton')
            self.assertEqual(project2099.proton_path(home),ge)
            with self.assertRaises(ValueError):project2099.proton_path(home,preferred='Proton 11.0')

if __name__=='__main__':unittest.main()
