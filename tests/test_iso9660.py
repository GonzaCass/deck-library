import pathlib,struct,tempfile,threading,unittest
from deck_library import iso9660,iso_import
from deck_library.ports import Cancelled

SECTOR=2048

def both(value,size=4):return struct.pack('<I',value)+struct.pack('>I',value)

def record(name,extent,length,flags=0,raw=None):
    ident=raw if raw is not None else name.encode()
    size=33+len(ident)+(1 if len(ident)%2==0 else 0)
    data=bytearray(size);data[0]=size;data[2:10]=both(extent);data[10:18]=both(length);data[25]=flags;data[32]=len(ident);data[33:33+len(ident)]=ident
    return bytes(data)

def pad(blob):return blob+bytes(-len(blob)%SECTOR)

def build(files,ps3=True,encrypted=False,split_big=False):
    """A small ISO 9660 image: files is {path: bytes}; a path with '/' makes folders. split_big stores the first file as two extents (multi-extent)."""
    tree={}
    for path,data in files.items():
        node=tree
        parts=path.split('/')
        for part in parts[:-1]:node=node.setdefault(part,{})
        node[parts[-1]]=data
    blocks=[];next_block=[19]  # 16 = volume descriptor, 17 = terminator, 18 = root directory
    placed={}
    def allocate(data):
        start=next_block[0];blocks.append((start,data));next_block[0]+=max(1,-(-len(data)//SECTOR));return start
    def layout(node,own,parent):
        entries=[record('',own,0,2,b'\x00'),record('',parent,0,2,b'\x01')];children=[]
        for name,value in sorted(node.items()):
            if isinstance(value,dict):
                directory=next_block[0];next_block[0]+=1;children.append((name,value,directory));entries.append(record(name,directory,SECTOR,2))
            elif split_big and name==sorted(node)[0] and len(value)>SECTOR:
                half=SECTOR*(len(value)//SECTOR//2) or SECTOR;first=allocate(value[:half]);second=allocate(value[half:])
                entries.append(record(name+';1',first,half,0x80));entries.append(record(name+';1',second,len(value)-half,0))
            else:entries.append(record(name+';1',allocate(value),len(value)))
        table=pad(b''.join(entries));placed[own]=table
        for name,value,directory in children:layout(value,directory,own)
    layout(tree,18,18)
    total=next_block[0];image=bytearray(total*SECTOR)
    primary=bytearray(SECTOR);primary[0]=1;primary[1:6]=b'CD001';primary[6]=1;primary[40:72]=b'PS3VOLUME'.ljust(32) if ps3 else b'DATA'.ljust(32)
    primary[128:130]=struct.pack('<H',SECTOR);primary[156:190]=record('',18,len(placed[18]),2,b'\x00')[:34]
    image[16*SECTOR:17*SECTOR]=primary;end=bytearray(SECTOR);end[0]=255;end[1:6]=b'CD001';image[17*SECTOR:18*SECTOR]=end
    for block,table in placed.items():image[block*SECTOR:block*SECTOR+len(table)]=table
    for block,data in blocks:image[block*SECTOR:block*SECTOR+len(data)]=data
    if encrypted:image[0xF70:0xF70+16]=b'Encrypted 3K BLD'
    return bytes(image)

GAME={'PS3_DISC.SFB':b'sfb','PS3_GAME/PARAM.SFO':b'sfo','PS3_GAME/USRDIR/EBOOT.BIN':b'eboot'*1000,'PS3_GAME/USRDIR/data/big.bin':bytes(range(256))*50}

class Iso9660Tests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def write(self,data,name='game.iso'):
        path=self.root/name;path.write_bytes(data);return path

    def test_a_ps3_disc_is_recognised_and_other_images_are_not(self):
        self.assertEqual(iso9660.sniff(self.write(build(GAME))),'ps3');self.assertEqual(iso9660.sniff(self.write(build({'a.txt':b'x'},ps3=False),'data.iso')),'iso9660')
        self.assertEqual(iso9660.sniff(self.write(bytes(0x9000),'blank.iso')),'');self.assertEqual(iso9660.sniff(self.root/'missing.iso'),'')

    def test_every_file_is_extracted_with_its_folders_and_verified(self):
        source=self.write(build(GAME));result=iso_import.extract_folder(source,self.root/'out')
        folder=pathlib.Path(result['path']);self.assertEqual((result['kind'],result['files']),('ps3',len(GAME)))
        for path,data in GAME.items():self.assertEqual((folder/path).read_bytes(),data)
        self.assertEqual(result['size'],sum(len(v) for v in GAME.values()));self.assertFalse(any(p.name.startswith('.deck-library-iso-') for p in (self.root/'out').iterdir()))

    def test_a_file_split_in_several_extents_is_joined(self):
        files={'PS3_GAME/PARAM.SFO':b'sfo','PS3_GAME/USRDIR/A.BIN':bytes(range(256))*40,'PS3_GAME/USRDIR/EBOOT.BIN':b'e'}
        source=self.write(build(files,split_big=True));result=iso_import.extract_folder(source,self.root/'out')
        self.assertEqual((pathlib.Path(result['path'])/'PS3_GAME/USRDIR/A.BIN').read_bytes(),files['PS3_GAME/USRDIR/A.BIN'])

    def test_an_encrypted_dump_and_a_disc_without_ps3_game_are_refused_before_extracting(self):
        with self.assertRaisesRegex(ValueError,'cifrada'):iso_import.extract_folder(self.write(build(GAME,encrypted=True)),self.root/'out')
        with self.assertRaisesRegex(ValueError,'PS3_GAME'):iso_import.extract_folder(self.write(build({'readme.txt':b'x'}),'other.iso'),self.root/'out')
        self.assertFalse((self.root/'out/game').exists())

    def test_other_data_discs_extract_too_and_the_source_is_never_modified(self):
        source=self.write(build({'Folder/a.txt':b'hello'},ps3=False));before=source.read_bytes()
        result=iso_import.extract_folder(source,self.root/'out');self.assertEqual(result['kind'],'iso9660');self.assertEqual((pathlib.Path(result['path'])/'Folder/a.txt').read_bytes(),b'hello');self.assertEqual(source.read_bytes(),before)

    def test_a_truncated_image_an_existing_destination_and_cancelling_leave_nothing_behind(self):
        data=build(GAME)
        with self.assertRaises(ValueError):iso_import.extract_folder(self.write(data[:len(data)//2],'cut.iso'),self.root/'out')
        source=self.write(data);iso_import.extract_folder(source,self.root/'out')
        with self.assertRaisesRegex(ValueError,'ya existe'):iso_import.extract_folder(source,self.root/'out')
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):iso_import.extract_folder(source,self.root/'other',cancel=cancel)
        self.assertFalse((self.root/'other/game').exists())

    def test_hostile_indexes_are_rejected(self):
        data=bytearray(build(GAME));start=data.find(b'PS3_DISC.SFB;1')-33;data[start+2:start+10]=both(10**7)  # a file record points outside the image
        with self.assertRaises(ValueError):iso_import.extract_folder(self.write(bytes(data),'bad.iso'),self.root/'out')
        loop=bytearray(build({'a/b.txt':b'x'},ps3=False));loop[18*SECTOR+68+2:18*SECTOR+68+10]=both(18)
        with self.assertRaises(ValueError):iso_import.extract_folder(self.write(bytes(loop),'loop.iso'),self.root/'out2')

if __name__=='__main__':unittest.main()
