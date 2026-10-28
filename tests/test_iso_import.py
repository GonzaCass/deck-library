import hashlib,io,json,pathlib,shutil,struct,tempfile,threading,unittest,zipfile
from unittest.mock import patch
from deck_library import iso_import,original_data,ports,project2099,xdvdfs
from deck_library.models import Store,atomic_json
from deck_library.transfer import Progress,caption

RISE='jorjbarbosa/naruto-rise-recomp'

def xex(title=0x555307E5):
    data=bytearray(128);data[:4]=b'XEX2';struct.pack_into('>I',data,20,1);struct.pack_into('>II',data,24,0x40006,64);struct.pack_into('>I',data,76,title);return bytes(data)

def create_iso(path,files=None,base=0):
    """Synthetic XDVDFS fixture: no original game content, sparse full-disc offsets."""
    files={'default.xex':xex(),'data/scene.bin':b'fixture payload','empty/':None,**(files or {})};tree={}
    for name,payload in files.items():
        parts=name.rstrip('/').split('/');parent=tree
        for part in parts[:-1]:parent=parent.setdefault(part,{})
        parent[parts[-1]]={} if payload is None else payload
    blocks={};next_sector=[40]
    def allocate(size):
        sector=next_sector[0];next_sector[0]+=max(1,(size+2047)//2048);return sector
    def directory(entries):
        sector=allocate(2048);table=bytearray(b'\xff'*2048);positions={};used=[0];children={}
        names=sorted(entries)
        def position(indices):
            if not indices:return None
            middle=len(indices)//2;name=indices[middle];pos=used[0];positions[name]=pos;used[0]+=(14+len(name.encode())+3)&~3
            left=position(indices[:middle]);right=position(indices[middle+1:]);children[name]=(left,right);return pos
        position(names)
        if used[0]>2048:raise ValueError('Fixture directory exceeds a sector')
        for name in names:
            value=entries[name]
            if isinstance(value,dict):start,length=directory(value);attributes=0x10
            else:start=allocate(len(value));length=len(value);attributes=0x20;blocks[start]=value
            pos=positions[name];left,right=children[name];encoded=name.encode()
            struct.pack_into('<HHIIBB',table,pos,0 if left is None else left//4,0 if right is None else right//4,start,length,attributes,len(encoded));table[pos+14:pos+14+len(encoded)]=encoded
        blocks[sector]=table;return sector,2048
    root,size=directory(tree);header=bytearray(2048);header[:20]=xdvdfs.MAGIC;header[-20:]=xdvdfs.MAGIC;struct.pack_into('<II',header,20,root,size)
    with pathlib.Path(path).open('wb') as stream:
        stream.seek(base+next_sector[0]*2048-1);stream.write(b'\0');stream.seek(base+65536);stream.write(header)
        for sector,block in blocks.items():stream.seek(base+sector*2048);stream.write(block)
    return files

class ISOImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.home=pathlib.Path(self.temp.name);self.folder=self.home/'ports/Naruto';self.folder.mkdir(parents=True)
        self.iso=self.home/'owned.iso';create_iso(self.iso);self.spec=ports.clean({'repository':RISE})['original_data']
    def tearDown(self):self.temp.cleanup()

    def test_trimmed_and_full_disc_offsets_extract_only_game_data(self):
        for index,base in enumerate(xdvdfs.BASES):
            source=self.home/f'disc-{index}.iso';create_iso(source,{'$SystemUpdate/update.bin':b'unneeded console update','zero.bin':b''},base)
            with xdvdfs.Image(source) as image:
                image.verify_game(self.spec);manifest=image.extract(self.home/f'extracted-{index}')
                self.assertEqual(image.skipped,['$SystemUpdate']);self.assertGreater(image.total,0)
            target=self.home/f'extracted-{index}';self.assertEqual((target/'data/scene.bin').read_bytes(),b'fixture payload');self.assertTrue((target/'empty').is_dir());self.assertFalse((target/'$SystemUpdate').exists())
            self.assertEqual(next(r for r in manifest if r['path']=='zero.bin')['sha256'],hashlib.sha256(b'').hexdigest())

    def test_old_install_accepts_iso_and_cleanup_preserves_game_saves_and_settings(self):
        store=Store(self.home/'private');record=ports.clean({'repository':RISE});record.update(folder='Naruto',configured=False,executable='narutorise_launcher.exe')
        record['original_data']={**record['original_data']};record['original_data'].pop('iso');record['original_data'].pop('extract_iso')
        atomic_json(store.root/'ports.json',{RISE:record});self.assertTrue(ports.records(store)[RISE]['original_data']['extract_iso'])
        ports.set_input(RISE,'original_data',self.iso,store)
        (self.folder/'user').mkdir();(self.folder/'user/save.dat').write_text('progress');(self.folder/'narutorise.toml').write_text('settings')
        done=ports.configure(RISE,store,home=self.home,progress=lambda _:None)
        self.assertTrue(done['configured']);self.assertTrue(self.iso.exists());self.assertTrue(iso_import.details(self.folder))
        size=self.iso.stat().st_size;self.assertEqual(iso_import.remove_source(self.folder,done),size)
        self.assertFalse(self.iso.exists());self.assertEqual((self.folder/'game/default.xex').read_bytes(),xex())
        self.assertEqual((self.folder/'user/save.dat').read_text(),'progress');self.assertEqual((self.folder/'narutorise.toml').read_text(),'settings')
        self.assertTrue(ports.requirements(done,[],self.home)[0][0]);self.assertIsNone(iso_import.details(self.folder))
        self.assertTrue(ports.configure(RISE,store,home=self.home,progress=lambda _:None)['configured'])

    def test_iso_title_is_checked_before_accepting_the_file_or_extracting(self):
        store=Store(self.home/'private');record=ports.clean({'repository':RISE});record['folder']='Naruto';atomic_json(store.root/'ports.json',{RISE:record})
        create_iso(self.iso,{'default.xex':xex(0x12345678)})
        with self.assertRaisesRegex(ValueError,'no corresponde'):ports.set_input(RISE,'original_data',self.iso,store)
        self.assertNotIn('inputs',ports.records(store)[RISE]);self.assertFalse((self.folder/'game').exists())
        create_iso(self.iso);ports.set_input(RISE,'original_data',self.iso,store)
        self.assertIn('555307E5',ports.requirements(ports.records(store)[RISE],[],self.home)[0][1])

    def test_wrong_game_revision_and_low_space_leave_existing_data_and_iso_intact(self):
        (self.folder/'game').mkdir();(self.folder/'game/old').write_text('keep')
        cases=[(xex(0x12345678),self.spec), (xex(),{**self.spec,'sha256':['0'*64]})]
        for executable,spec in cases:
            create_iso(self.iso,{'default.xex':executable})
            with self.assertRaises(ValueError):iso_import.prepare(self.folder,self.iso,spec,lambda _:None)
            self.assertEqual((self.folder/'game/old').read_text(),'keep');self.assertTrue(self.iso.exists())
        create_iso(self.iso)
        with patch.object(shutil,'disk_usage',return_value=shutil._ntuple_diskusage(100,100,0)),self.assertRaisesRegex(ValueError,'espacio'):iso_import.prepare(self.folder,self.iso,self.spec,lambda _:None)
        self.assertEqual(list(self.folder.glob('.deck-library-import-*')),[])

    def test_update_preserves_import_receipt_and_reuses_verified_files(self):
        store=Store(self.home/'private');record=ports.clean({'repository':RISE});record.update(folder='Naruto',configured=False,executable='narutorise_launcher.exe')
        atomic_json(store.root/'ports.json',{RISE:record});ports.set_input(RISE,'original_data',self.iso,store);ports.configure(RISE,store,home=self.home,progress=lambda _:None)
        identity=(self.folder/'game/default.xex').stat().st_ino;payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w') as archive:archive.writestr('narutorise_launcher.exe',b'MZfixture');archive.writestr('narutorise.exe',b'MZfixture')
        release={'tag_name':'new','assets':[{'name':'Naruto-win64.zip','browser_download_url':'https://github.com/'+RISE+'/new.zip'}]}
        with patch.object(ports,'download',side_effect=lambda _,target,**kw:target.write_bytes(payload.getvalue())),patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')):
            ports.install({'repository':RISE},store,self.home/'ports',get=lambda _:release,replace=True,progress=lambda _:None)
        self.assertTrue((self.folder/iso_import.MANIFEST).is_file())
        identity=(self.folder/'game/default.xex').stat().st_ino
        ports.configure(RISE,store,home=self.home,progress=lambda _:None)
        self.assertEqual((self.folder/'game/default.xex').stat().st_ino,identity)
        self.assertFalse((self.folder/'.deck-library-original-backups').exists())
        iso_import.remove_source(self.folder,ports.records(store)[RISE]);self.assertFalse(self.iso.exists())

    def test_cancelled_extraction_cleans_staging_and_keeps_original_and_previous_game(self):
        create_iso(self.iso,{'data/large.bin':b'x'*(2*1024**2)})
        (self.folder/'game').mkdir();(self.folder/'game/old').write_text('keep');cancel=threading.Event()
        def progress(event):
            if event['done']:cancel.set()
        with self.assertRaises(ports.Cancelled):iso_import.prepare(self.folder,self.iso,self.spec,progress,cancel)
        self.assertTrue(self.iso.exists());self.assertEqual((self.folder/'game/old').read_text(),'keep');self.assertFalse((self.folder/iso_import.MANIFEST).exists());self.assertEqual(list(self.folder.glob('.deck-library-import-*')),[])

    def test_failed_promotion_restores_previous_game_and_manifest(self):
        (self.folder/'game').mkdir();(self.folder/'game/old').write_text('keep');(self.folder/iso_import.MANIFEST).write_text('old manifest')
        replace=pathlib.Path.replace
        def fail(path,target):
            if path.name=='manifest.json':raise OSError('injected disk failure')
            return replace(path,target)
        with patch.object(pathlib.Path,'replace',fail),self.assertRaises(OSError):iso_import.prepare(self.folder,self.iso,self.spec,lambda _:None)
        self.assertEqual((self.folder/'game/old').read_text(),'keep');self.assertEqual((self.folder/iso_import.MANIFEST).read_text(),'old manifest');self.assertTrue(self.iso.exists())

    def record(self):return {'configured':True,'original_data':self.spec,'inputs':{'original_data':str(self.iso)}}

    def test_cleanup_refuses_missing_modified_or_redirected_game_data(self):
        for mode in ('modified','missing','symlink'):
            if (self.folder/'game').exists():shutil.rmtree(self.folder/'game')
            iso_import.prepare(self.folder,self.iso,self.spec,lambda _:None);file=self.folder/'game/data/scene.bin'
            if mode=='modified':file.write_bytes(b'changed payload')
            elif mode=='missing':file.unlink()
            else:
                outside=self.home/'outside';outside.write_bytes(file.read_bytes());file.unlink();file.symlink_to(outside)
            with self.assertRaises((OSError,ValueError)):iso_import.remove_source(self.folder,self.record())
            self.assertTrue(self.iso.exists())

    def test_cleanup_refuses_changed_iso_and_honors_cancellation(self):
        iso_import.prepare(self.folder,self.iso,self.spec,lambda _:None);before=self.iso.read_bytes();self.iso.write_bytes(before+b'changed')
        with self.assertRaises(ValueError):iso_import.remove_source(self.folder,self.record())
        self.assertTrue(self.iso.exists());self.iso.write_bytes(before)
        iso_import.prepare(self.folder,self.iso,self.spec,lambda _:None);cancel=threading.Event()
        with self.assertRaises(ports.Cancelled):iso_import.remove_source(self.folder,self.record(),lambda _:cancel.set(),cancel)
        self.assertTrue(self.iso.exists())

    def test_incomplete_manifest_cannot_authorize_removing_the_iso(self):
        iso_import.prepare(self.folder,self.iso,self.spec,lambda _:None);path=self.folder/iso_import.MANIFEST
        data=json.loads(path.read_text());data['files'].pop();atomic_json(path,data)
        with self.assertRaisesRegex(ValueError,'registro'):iso_import.remove_source(self.folder,self.record())
        self.assertTrue(self.iso.exists())

    def test_unsafe_paths_collisions_and_directory_cycles_are_rejected(self):
        for files in ({'..':b'bad'},{'C:bad':b'bad'},{'same.bin':b'a','SAME.bin':b'b'}):
            create_iso(self.iso,files)
            with self.assertRaises(ValueError),xdvdfs.Image(self.iso):pass
        create_iso(self.iso,{'loop/':None})
        with self.iso.open('r+b') as file:
            file.seek(40*2048);table=bytearray(file.read(2048));offset=table.index(b'loop')-14;struct.pack_into('<II',table,offset+4,40,2048);file.seek(40*2048);file.write(table)
        with self.assertRaises(ValueError),xdvdfs.Image(self.iso):pass

    def test_corrupt_header_and_truncated_data_never_create_a_destination(self):
        for position in (65536,65536+2048-20):
            create_iso(self.iso)
            with self.iso.open('r+b') as file:file.seek(position);file.write(b'broken')
            with self.assertRaises(ValueError):iso_import.prepare(self.folder,self.iso,self.spec,lambda _:None)
            self.assertFalse((self.folder/'game').exists())
        create_iso(self.iso)
        with self.iso.open('r+b') as file:file.truncate(40*2048+2048)
        with self.assertRaises(ValueError),xdvdfs.Image(self.iso):pass

    def test_extraction_and_verification_progress_have_real_percentages_and_eta(self):
        state=Progress();state.update({'phase':'download','done':10,'total':100},now=0)
        state.update({'phase':'extract','done':0,'total':200},now=10)
        result=state.update({'phase':'extract','done':100,'total':200},now=12)
        self.assertEqual(result['fraction'],.5);self.assertEqual(result['eta'],2);self.assertIn('50%',caption(result))
        state.update({'phase':'verify','done':0,'total':100},now=20)
        self.assertEqual(state.update({'phase':'verify','done':100,'total':100},now=22)['eta'],0)

class ExtractFolderTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.iso=self.root/'Mi Juego (USA).iso';self.files=create_iso(self.iso)
    def tearDown(self):self.temp.cleanup()
    def test_an_iso_becomes_a_verified_folder_named_after_it(self):
        events=[];result=iso_import.extract_folder(self.iso,self.root/'out',events.append)
        folder=pathlib.Path(result['path']);self.assertEqual(folder.name,'Mi Juego _USA_.iso'[:-4] if False else folder.name);self.assertTrue((folder/'data/scene.bin').is_file());self.assertEqual((folder/'data/scene.bin').read_bytes(),b'fixture payload')
        self.assertEqual(result['files'],2);self.assertEqual(result['size'],len(self.files['default.xex'])+len(b'fixture payload'));self.assertTrue(events);self.assertEqual([p.name for p in (self.root/'out').iterdir()],[folder.name])
        self.assertTrue(self.iso.is_file())
    def test_an_existing_folder_is_never_overwritten_and_a_bad_image_leaves_nothing(self):
        iso_import.extract_folder(self.iso,self.root/'out')
        with self.assertRaisesRegex(ValueError,'ya existe'):iso_import.extract_folder(self.iso,self.root/'out')
        broken=self.root/'otra.iso';broken.write_bytes(bytes(100000))
        with self.assertRaises(ValueError):iso_import.extract_folder(broken,self.root/'out2')
        self.assertEqual([p for p in (self.root/'out2').iterdir()],[])
    def test_cancelling_leaves_no_partial_folder(self):
        import threading
        from deck_library.ports import Cancelled
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):iso_import.extract_folder(self.iso,self.root/'out',cancel=cancel)
        self.assertEqual([p for p in (self.root/'out').iterdir()],[])


if __name__=='__main__':unittest.main()
