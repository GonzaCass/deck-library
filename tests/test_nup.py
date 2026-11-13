"""NUP containers (unencrypted Switch / Switch 2 dumps): reading, layout, verification and refusal of malformed files."""
import hashlib,pathlib,struct,tempfile,threading,unittest
from deck_library import nup

try:
    from compression import zstd
except ImportError:
    zstd=None

def build(packages,codec=None,mutate=None):
    """A spec-conformant NUP v1 file. packages: [{'kind','title_id','version','files':{path:bytes},'title','display'}].
    `mutate(state)` may change records before they are written, to produce malformed files."""
    codec=(1 if zstd else 0) if codec is None else codec
    strings=bytearray();names={}
    def intern(text):
        raw=text.encode()
        if raw not in names:names[raw]=len(strings);strings.extend(raw)
        return names[raw],len(raw)
    dirs=[];files=[];children_of={};blobs=[]
    def make_dir(name):
        dirs.append({'name':intern(name),'children':[]});return len(dirs)-1
    package_rows=[]
    for package in packages:
        root=make_dir('');tree={}
        for path,data in package['files'].items():
            node=tree
            for part in path.split('/')[:-1]:node=node.setdefault(part,{})
            node[path.split('/')[-1]]=data
        def fill(index,node):
            for name in sorted(node,key=lambda n:n.encode()):
                value=node[name]
                if isinstance(value,dict):
                    child=make_dir(name);dirs[index]['children'].append(('d',child));fill(child,value)
                else:
                    stored=zstd.compress(value) if codec==1 and zstd else value
                    files.append({'name':intern(name),'data':value,'stored':stored,'codec':(codec if (codec==0 or zstd) else 0) if value else 0});dirs[index]['children'].append(('f',len(files)-1))
        fill(root,tree)
        package_rows.append({'title_id':package.get('title_id',0x0400000000001000),'root':root,'version':package.get('version',0),'kind':{'base':0,'update':1,'addon':2}[package['kind']],
                             'meta':b''.join(struct.pack('<HHI',kind,0,len(value))+value for kind,value in ((5,package.get('title','').encode()),(4,package.get('display','').encode())) if value)})
    state={'dirs':dirs,'files':files,'packages':package_rows}
    if mutate:mutate(state)
    children=[];first=[]
    for entry in dirs:
        first.append(len(children))
        for kind,index in entry['children']:children.append(index if kind=='d' else len(dirs)+index)
    head=struct.Struct('<4sIQQQQQ')
    toc_records=head.size+0x40*len(package_rows)+0x18*len(dirs)+0x50*len(files)+4*len(children)
    pool_off=toc_records;toc_size=pool_off+len(strings)
    blob_offset=(0x80+toc_size+15)//16*16;cursor=blob_offset;blob=bytearray()
    for record in files:
        if not record['data']:record['offset']=0;continue
        pad=(-cursor)%16;blob.extend(b'\0'*pad);cursor+=pad;record['offset']=record.get('offset_override',cursor);blob.extend(record['stored']);cursor+=len(record['stored'])
    metas=[]
    for row in package_rows:
        pad=(-cursor)%16;blob.extend(b'\0'*pad);cursor+=pad;row['meta_offset']=cursor if row['meta'] else 0;blob.extend(row['meta']);cursor+=len(row['meta'])
    toc=bytearray(head.pack(b'TOC\x01',len(package_rows),len(dirs),len(files),pool_off,len(strings),0))
    for row in package_rows:toc+=struct.pack('<QIIIIBBHIQI20s',row['title_id'],row['root'],nup.NONE,nup.NONE,row['version'],row['kind'],0,0,0,row['meta_offset'],len(row['meta']),b'')
    for index,entry in enumerate(dirs):toc+=struct.pack('<IIIIQ',*entry['name'],first[index],len(entry['children']),0)
    for record in files:
        toc+=struct.pack('<IIQQQ32sBBH12s',*record['name'],len(record['data']),record['offset'],len(record['stored']) if record['data'] else 0,hashlib.sha256(record['data']).digest() if 'digest' not in record else record['digest'],record['codec'],0,0,b'')
    toc+=struct.pack(f'<{len(children)}I',*children)+strings
    total=blob_offset+len(blob)
    head_block=struct.pack('<4sHHQQ32sQQII16s32s',b'NUP\x01',0x80,1,0x80,len(toc),hashlib.sha256(toc).digest(),blob_offset,total,len(package_rows),0,b'\0'*16,b'')
    return head_block+bytes(toc)+b'\0'*(blob_offset-0x80-len(toc))+bytes(blob)

GAME=[{'kind':'base','title_id':0x0400ABCD00010000,'title':'Juego de prueba','display':'1.0.0','files':{'exefs/main':b'NSO0'+b'm'*3000,'exefs/main.npdm':b'META','romfs/data/a.bin':b'A'*5000,'romfs/data/b.bin':b'base','romfs/empty.txt':b''}},
      {'kind':'update','title_id':0x0400ABCD00010800,'version':0x10100,'display':'1.1.0','files':{'exefs/main':b'NSO0'+b'u'*3000,'romfs/data/b.bin':b'patched'}},
      {'kind':'addon','title_id':0x0400ABCD00011001,'files':{'romfs/dlc.bin':b'dlc'}}]

class NupTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def write(self,data,name='game.nup'):
        path=self.root/name;path.write_bytes(data);return path

    def test_packages_and_titles_are_read(self):
        with nup.Container(self.write(build(GAME))) as container:
            self.assertEqual([p['kind'] for p in container.packages],['base','update','addon'])
            self.assertEqual(container.title,'Juego de prueba');self.assertEqual(container.packages[1]['display_version'],'1.1.0')
            self.assertEqual(container.packages[0]['title_id'],'0400ABCD00010000')

    def test_merged_extraction_lays_the_newest_update_over_the_base(self):
        result=nup.extract_folder(self.write(build(GAME)),self.root/'out')
        out=pathlib.Path(result['path']);self.assertEqual(out.name,'game')
        self.assertEqual((out/'exefs/main').read_bytes()[4:5],b'u');self.assertEqual((out/'romfs/data/b.bin').read_bytes(),b'patched')
        self.assertEqual((out/'romfs/data/a.bin').read_bytes(),b'A'*5000);self.assertEqual((out/'exefs/main.npdm').read_bytes(),b'META')
        self.assertEqual((out/'romfs/empty.txt').read_bytes(),b'');self.assertEqual((out/'dlc/0400ABCD00011001/romfs/dlc.bin').read_bytes(),b'dlc')
        self.assertEqual(result['title'],'Juego de prueba')

    def test_full_extraction_keeps_base_updates_and_dlc_apart(self):
        out=pathlib.Path(nup.extract_folder(self.write(build(GAME)),self.root/'out',merge=False)['path'])
        self.assertEqual((out/'base/romfs/data/b.bin').read_bytes(),b'base');self.assertEqual((out/'updates/1.1.0/romfs/data/b.bin').read_bytes(),b'patched')
        self.assertTrue((out/'dlc/0400ABCD00011001/romfs/dlc.bin').is_file())

    def test_raw_files_work_without_any_zstd(self):
        out=pathlib.Path(nup.extract_folder(self.write(build(GAME,codec=0)),self.root/'out')['path'])
        self.assertEqual((out/'romfs/data/b.bin').read_bytes(),b'patched')

    def test_a_damaged_index_is_refused(self):
        data=bytearray(build(GAME));data[0x80+0x40]^=1
        with self.assertRaisesRegex(ValueError,'SHA-256'):nup.Container(self.write(bytes(data)))

    def test_a_damaged_file_leaves_no_folder_behind(self):
        data=bytearray(build(GAME,codec=0));index=bytes(data).index(b'A'*5000);data[index]^=1
        with self.assertRaisesRegex(ValueError,'SHA-256'):nup.extract_folder(self.write(bytes(data)),self.root/'out')
        self.assertEqual([p.name for p in (self.root/'out').iterdir()],[])

    def test_a_truncated_file_is_refused(self):
        with self.assertRaisesRegex(ValueError,'incompleto'):nup.Container(self.write(build(GAME)[:-10]))

    def test_names_that_could_leave_the_folder_are_refused(self):
        for bad in ('..','a\\b','.'):
            data=build([{'kind':'base','files':{bad:b'1'}}],codec=0)
            with self.assertRaisesRegex(ValueError,'nombre'):nup.extract_folder(self.write(data,f'bad{len(bad)}.nup'),self.root/'out')
        self.assertEqual([p.name for p in self.root.iterdir() if p.is_dir()],['out']);self.assertEqual(list((self.root/'out').iterdir()),[])

    def test_a_folder_that_contains_itself_is_refused(self):
        def mutate(state):state['dirs'][1]['children'].append(('d',1))
        data=build([{'kind':'base','files':{'romfs/a':b'1'}}],codec=0,mutate=mutate)
        with self.assertRaisesRegex(ValueError,'carpetas|nombre'):nup.extract_folder(self.write(data),self.root/'out')

    def test_extents_outside_the_data_region_are_refused(self):
        def mutate(state):state['files'][0]['offset_override']=16
        data=build([{'kind':'base','files':{'a':b'x'*40}}],codec=0,mutate=mutate)
        with self.assertRaisesRegex(ValueError,'fuera'):nup.Container(self.write(data))

    def test_unknown_compression_is_refused(self):
        def mutate(state):state['files'][0]['codec']=2
        data=build([{'kind':'base','files':{'a':b'x'}}],codec=0,mutate=mutate)
        with self.assertRaisesRegex(ValueError,'compresión'):nup.Container(self.write(data))

    @unittest.skipUnless(zstd,'needs Python zstd to build compressed fixtures')
    def test_a_file_that_expands_beyond_its_declared_size_is_stopped(self):
        def mutate(state):state['files'][0]['stored']=zstd.compress(b'\0'*(8<<20))
        data=build([{'kind':'base','files':{'a':b'\0'*16}}],codec=1,mutate=mutate)
        with self.assertRaisesRegex(ValueError,'declarados'):nup.extract_folder(self.write(data),self.root/'out')

    @unittest.skipUnless(zstd,'needs Python zstd to build compressed fixtures')
    def test_the_zstd_program_gives_the_same_result(self):
        import builtins,shutil
        if not shutil.which('zstd'):self.skipTest('zstd program not installed')
        real=builtins.__import__
        def without(name,*args,**kwargs):
            if name=='compression':raise ImportError
            return real(name,*args,**kwargs)
        builtins.__import__=without
        try:out=pathlib.Path(nup.extract_folder(self.write(build(GAME)),self.root/'out')['path'])
        finally:builtins.__import__=real
        self.assertEqual((out/'romfs/data/a.bin').read_bytes(),b'A'*5000)

    def test_cancel_stops_without_a_folder(self):
        from deck_library.ports import Cancelled
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):nup.extract_folder(self.write(build(GAME)),self.root/'out',cancel=cancel)
        self.assertEqual([p.name for p in (self.root/'out').iterdir()],[])

    def test_an_existing_folder_is_not_overwritten(self):
        (self.root/'out/game').mkdir(parents=True);(self.root/'out/game/keep').write_text('mine')
        with self.assertRaisesRegex(ValueError,'no está vacía'):nup.extract_folder(self.write(build(GAME)),self.root/'out')
        self.assertEqual((self.root/'out/game/keep').read_text(),'mine')

    def test_sniff(self):
        self.assertTrue(nup.sniff(self.write(build(GAME))));self.assertFalse(nup.sniff(self.write(b'PK\3\4','x.zip')))

if __name__=='__main__':unittest.main()
