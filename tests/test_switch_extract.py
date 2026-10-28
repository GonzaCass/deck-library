import os,pathlib,shutil,stat,struct,tarfile,tempfile,threading,unittest
from unittest.mock import patch
from deck_library import switch_extract as sx
from deck_library.models import Store

BASE_TID='01007ef00011e000';PATCH_TID='01007ef00011e800'
RIGHTS_BASE='01007ef00011e000'+'0000000000000007';RIGHTS_PATCH='01007ef00011e800'+'0000000000000007'
KEYS='header_key = '+'ab'*32+'\nmaster_key_00 = '+'cd'*16+'\n'

def ticket(rights,key,personalized=False,signature=0x10004):
    body=sx.TICKET_BODY[signature];data=bytearray(body+0x2C0);data[:4]=signature.to_bytes(4,'little')
    data[body+0x40:body+0x50]=bytes.fromhex(key);data[body+0x141]=1 if personalized else 0;data[body+0x160:body+0x170]=bytes.fromhex(rights)
    return bytes(data)

def info(kind,tid,size,rights=''):
    lines=['NCA:','Magic:                              NCA3','Content Size:                       0x%012X'%size,'Title ID:                           '+tid,'Content Type:                       '+kind]
    if rights:lines.append('Rights ID:                          '+rights.upper())
    return lines

class FakeHactool:
    """Stands in for hactool: lays out the files the real tool would and records every command."""
    def __init__(self,size=1000,omit_main=False,patch_tid=PATCH_TID,noisy=False):
        self.calls=[];self.size=size;self.omit_main=omit_main;self.patch_tid=patch_tid;self.noisy=noisy;self.title_keys=[]
    def __call__(self,command,progress=print,until=None,sandbox=True,env=None,cwd=None,**kw):
        self.calls.append((command,dict(env or {})));args=command[1:]
        def value(prefix):return next((a.split('=',1)[1] for a in args if a.startswith(prefix)),None)
        if '-t' in args and args[args.index('-t')+1] in ('pfs0','xci'):
            folder=pathlib.Path(value('--pfs0dir=') or value('--securedir='));updating=folder.name.endswith('-1')
            (folder/('update.nca' if updating else 'game.nca')).write_bytes(b'x');(folder/('meta.cnmt.nca')).write_bytes(b'x')
            (folder/'a.tik').write_bytes(ticket(RIGHTS_PATCH if updating else RIGHTS_BASE,('22' if updating else '11')*16));progress('Saving a.tik')
        elif '-i' in args:
            name=pathlib.Path(args[-1]).name
            for line in (info('Program',self.patch_tid,self.size,RIGHTS_PATCH) if name=='update.nca' else info('Program',BASE_TID,self.size,RIGHTS_BASE)):progress(line)
            title=pathlib.Path(env['HOME'],'.switch/title.keys');self.title_keys.append(title.read_text() if title.exists() else None)
        else:
            exefs=pathlib.Path(value('--exefsdir='));romfs=pathlib.Path(value('--romfsdir='))
            if not self.omit_main:(exefs/'main').write_bytes(b'NSO0');(exefs/'main.npdm').write_bytes(b'META')
            (romfs/'Pack').mkdir();(romfs/'Pack/Dungeon.pack').write_bytes(b'data');(romfs/'Mod').write_bytes(b'x')
            if self.noisy:progress('Key: '+'ab'*32)
        return 0

class TicketTests(unittest.TestCase):
    def test_a_common_ticket_gives_the_rights_id_and_the_encrypted_title_key(self):
        for signature in sx.TICKET_BODY:self.assertEqual(sx.parse_ticket(ticket(RIGHTS_BASE,'11'*16,signature=signature)),(RIGHTS_BASE,'11'*16))
    def test_personalized_unknown_and_short_tickets_are_refused(self):
        with self.assertRaisesRegex(ValueError,'personalizado'):sx.parse_ticket(ticket(RIGHTS_BASE,'11'*16,personalized=True))
        with self.assertRaises(ValueError):sx.parse_ticket(b'\x01\x02\x03\x04'+bytes(0x400))
        with self.assertRaises(ValueError):sx.parse_ticket(b'\x04\x00\x01\x00')

class SmallHelperTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.home=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_keys_are_found_in_emulator_folders_and_must_look_complete(self):
        keys=self.home/'.local/share/eden/keys/prod.keys';keys.parent.mkdir(parents=True);keys.write_text(KEYS)
        self.assertEqual(sx.find_keys(self.home),[str(keys)]);self.assertEqual(sx.check_keys(keys),str(keys))
        incomplete=self.home/'bad.keys';incomplete.write_text('header_key = '+'ab'*32+'\n')
        with self.assertRaisesRegex(ValueError,'prod.keys completo'):sx.check_keys(incomplete)
        with self.assertRaises(ValueError):sx.check_keys(self.home/'missing.keys')
    def test_containers_are_recognised_by_content(self):
        nsp=self.home/'a.bin';nsp.write_bytes(b'PFS0'+bytes(100));xci=self.home/'b.bin';xci.write_bytes(bytes(0x100)+b'HEAD'+bytes(100));other=self.home/'c.nsp';other.write_bytes(bytes(0x200))
        self.assertEqual(sx.container_kind(nsp),'nsp');self.assertEqual(sx.container_kind(xci),'xci')
        with self.assertRaisesRegex(ValueError,'ni un XCI'):sx.container_kind(other)
        compressed=self.home/'d.nsz';compressed.write_bytes(b'PFS0')
        with self.assertRaisesRegex(ValueError,'comprimidos'):sx.container_kind(compressed)
    def test_hactool_info_is_parsed_and_long_hex_never_reaches_the_screen(self):
        parsed=sx.parse_info(info('Program',BASE_TID,0x350000000,RIGHTS_BASE))
        self.assertEqual((parsed['type'],parsed['title_id'],parsed['size'],parsed['rights_id']),('Program',BASE_TID,0x350000000,RIGHTS_BASE))
        self.assertEqual(sx.parse_info(['Content Type:                       Control'])['type'],'Control')
        self.assertNotIn('ab'*12,sx.sanitize('Key: '+'ab'*32));self.assertEqual(sx.sanitize('Saving main'),'Saving main')

class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.out=self.root/'out'
        self.keys=self.root/'prod.keys';self.keys.write_text(KEYS)
        self.base=self.root/'base.nsp';self.base.write_bytes(b'PFS0'+bytes(100));self.update=self.root/'update.nsp';self.update.write_bytes(b'PFS0'+bytes(100))
    def tearDown(self):self.temp.cleanup()
    def job(self,fake=None,**kw):
        self.messages=[];self.fake=fake or FakeHactool(**kw);return sx.Job('/fake/hactool',self.keys,progress=self.messages.append,run=self.fake)
    def test_a_base_game_becomes_exefs_and_romfs_under_its_title_id(self):
        result=self.job().convert(self.base,self.out)
        folder=self.out/BASE_TID;self.assertEqual(result['path'],str(folder));self.assertEqual(result['title'],'The Legend of Zelda: Breath of the Wild');self.assertFalse(result['update'])
        self.assertTrue((folder/'exefs/main').is_file());self.assertEqual(result['files'],2);self.assertEqual(sx.details(folder)['sources'],['base.nsp'])
        self.assertEqual([p.name for p in self.out.iterdir()],[BASE_TID])
        extraction=self.fake.calls[-1][0];self.assertIn('-t',extraction);self.assertFalse(any(a.startswith('--basenca') for a in extraction))
    def test_title_keys_go_to_a_private_home_and_keys_are_never_on_the_command_line(self):
        self.job().convert(self.base,self.out)
        command,env=self.fake.calls[0];self.assertTrue(env['HOME'].startswith(str(self.out)));self.assertEqual(command[2],str(self.keys))
        joined=' '.join(' '.join(c) for c,_ in self.fake.calls);self.assertNotIn('11'*16,joined);self.assertNotIn('ab'*32,joined)
        self.assertEqual(self.fake.title_keys[0],RIGHTS_BASE+' = '+'11'*16+'\n')
        self.assertFalse(any('.deck-library-switch' in p.name for p in self.out.iterdir()))
    def test_an_update_is_applied_over_the_base_nca_and_both_title_keys_are_known(self):
        result=self.job().convert(self.base,self.out,update=self.update)
        self.assertTrue(result['update']);extraction=self.fake.calls[-1][0]
        self.assertTrue(any(a.startswith('--basenca=') and a.endswith('game.nca') for a in extraction));self.assertTrue(extraction[-1].endswith('update.nca'))
        self.assertEqual(sx.details(self.out/BASE_TID)['sources'],['base.nsp','update.nsp'])
        self.assertIn(RIGHTS_BASE+' = '+'11'*16,self.fake.title_keys[-1]);self.assertIn(RIGHTS_PATCH+' = '+'22'*16,self.fake.title_keys[-1])
    def test_an_update_whose_header_carries_the_base_application_id_is_accepted(self):
        result=self.job(patch_tid=BASE_TID).convert(self.base,self.out,update=self.update);self.assertTrue(result['update'])
    def test_an_update_for_another_game_is_refused_and_leaves_nothing(self):
        with self.assertRaisesRegex(ValueError,'no corresponde'):self.job(patch_tid='0100000000001800').convert(self.base,self.out,update=self.update)
        self.assertEqual(list(self.out.iterdir()),[])
    def test_missing_exefs_main_fails_without_publishing(self):
        with self.assertRaisesRegex(ValueError,'exefs/main'):self.job(omit_main=True).convert(self.base,self.out)
        self.assertEqual(list(self.out.iterdir()),[])
    def test_converting_again_keeps_a_backup_and_a_foreign_folder_is_never_touched(self):
        self.job().convert(self.base,self.out);self.job().convert(self.base,self.out)
        self.assertEqual(len(list((self.out/'.deck-library-original-backups').iterdir())),1)
        foreign=self.root/'other';foreign.mkdir();(foreign/BASE_TID).mkdir();(foreign/BASE_TID/'mine.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError,'no es una conversión'):self.job().convert(self.base,foreign)
        self.assertEqual((foreign/BASE_TID/'mine.txt').read_text(),'keep')
    def test_not_enough_disk_is_reported_before_any_work(self):
        usage=shutil._ntuple_diskusage(100,99,1)
        with patch('shutil.disk_usage',return_value=usage),self.assertRaisesRegex(ValueError,'espacio suficiente'):self.job().convert(self.base,self.out)
        self.assertEqual(self.fake.calls,[])
    def test_cancelling_stops_the_conversion_and_cleans_up(self):
        from deck_library.ports import Cancelled
        cancel=threading.Event();fake=FakeHactool();inner=fake.__call__
        def run(command,**kw):
            result=inner(command,**kw)
            if '-i' in command:cancel.set()
            return result
        job=sx.Job('/fake/hactool',self.keys,progress=lambda text:None,cancel=cancel,run=run)
        with self.assertRaises(Cancelled):job.convert(self.base,self.out)
        self.assertEqual(list(self.out.iterdir()),[])
    def test_an_update_format_hactool_cannot_read_is_explained(self):
        def run(command,**kw):
            if '-i' in command and pathlib.Path(command[-1]).name=='update.nca':raise RuntimeError('Invalid BKTR layout!')
            return self.fake(command,**kw)
        self.fake=FakeHactool();job=sx.Job('/fake/hactool',self.keys,progress=lambda text:None,run=run)
        with self.assertRaisesRegex(ValueError,'BKTR'):job.convert(self.base,self.out,update=self.update)
        self.assertEqual(list(self.out.iterdir()),[])
    def test_tool_output_is_sanitized_before_it_reaches_progress(self):
        self.job(noisy=True).convert(self.base,self.out)
        self.assertFalse(any('ab'*12 in message for message in self.messages))

class FakeNstool:
    """Stands in for nstool: same layout the real one produced for a base game plus an update."""
    def __init__(self,patch_id=BASE_TID):self.calls=[];self.patch_id=patch_id
    def __call__(self,command,progress=print,until=None,sandbox=True,env=None,cwd=None,**kw):
        self.calls.append(command);args=command[3:]
        if args[:2]==['-x','/']:
            folder=pathlib.Path(args[2]);updating=folder.name.endswith('-1')
            (folder/('update.nca' if updating else 'game.nca')).write_bytes(b'x');(folder/'a.tik').write_bytes(ticket(RIGHTS_PATCH if updating else RIGHTS_BASE,('22' if updating else '11')*16));progress('Saving a.tik...')
        elif len(args)==1:
            name=pathlib.Path(args[0]).name;patch=name=='update.nca'
            for line in ('[NCA Header]','  Content Type:    Program','  Size:            0x%x'%1000,'  ProgID:          0x'+(self.patch_id if patch else BASE_TID),'  RightsId:        '+(RIGHTS_PATCH if patch else RIGHTS_BASE).upper()):progress(line)
        else:
            partition=args[args.index('-x')+1];folder=pathlib.Path(args[args.index('-x')+2])
            folder.mkdir(parents=True,exist_ok=True)
            if partition=='/0':(folder/'main').write_bytes(b'NSO0');(folder/'main.npdm').write_bytes(b'META')
            else:(folder/'Pack').mkdir();(folder/'Pack/Dungeon000.pack').write_bytes(b'data');progress('Saving '+str(folder/'Pack/Dungeon000.pack')+'...')
        return 0

class NstoolConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.out=self.root/'out'
        self.keys=self.root/'prod.keys';self.keys.write_text(KEYS)
        self.base=self.root/'base.nsp';self.base.write_bytes(b'PFS0'+bytes(100));self.update=self.root/'update.nsp';self.update.write_bytes(b'PFS0'+bytes(100))
    def tearDown(self):self.temp.cleanup()
    def test_the_backend_is_chosen_from_the_tool_name_and_nstool_is_preferred(self):
        self.assertEqual(sx.backend_of('/x/nstool'),'nstool');self.assertEqual(sx.backend_of('/x/hactool'),'hactool')
        script=self.root/'nstool';script.write_text('#!/bin/sh\necho "NSTool v1.9.2 (C) jakcron"\n');script.chmod(0o755)
        other=self.root/'hactool';other.write_text('#!/bin/sh\necho "hactool (c) SciresM."\n');other.chmod(0o755)
        self.assertEqual(sx.tool_path(preferences={'nstool_path':str(script),'hactool_path':str(other)}),str(script))
        self.assertEqual(sx.tool_path(preferences={'hactool_path':str(other)}),str(other))
    def test_a_base_game_and_its_update_are_extracted_by_partition_over_the_base_nca(self):
        fake=FakeNstool();messages=[];job=sx.Job('/fake/nstool',self.keys,progress=messages.append,run=fake)
        result=job.convert(self.base,self.out,update=self.update)
        self.assertTrue(result['update']);self.assertEqual(result['files'],1);self.assertTrue((self.out/BASE_TID/'exefs/main').is_file());self.assertTrue((self.out/BASE_TID/'romfs/Pack/Dungeon000.pack').is_file())
        extractions=[c for c in fake.calls if '/0' in c or '/1' in c];self.assertEqual(len(extractions),2)
        for command in extractions:self.assertIn('--basenca',command);self.assertTrue(command[command.index('--basenca')+1].endswith('game.nca'));self.assertTrue(command[-1].endswith('update.nca'))
        self.assertEqual(sx.details(self.out/BASE_TID)['tool']['name'],'nstool');self.assertTrue(any(m.startswith('Guardando') for m in messages))
        self.assertFalse(any('11'*16 in ' '.join(c) for c in fake.calls))
    def test_a_base_game_alone_needs_no_base_option(self):
        fake=FakeNstool();sx.Job('/fake/nstool',self.keys,progress=lambda t:None,run=fake).convert(self.base,self.out)
        self.assertFalse(any('--basenca' in c for c in fake.calls))
    def test_an_update_for_another_game_is_still_refused(self):
        fake=FakeNstool(patch_id='0100000000001800')
        with self.assertRaisesRegex(ValueError,'no corresponde'):sx.Job('/fake/nstool',self.keys,progress=lambda t:None,run=fake).convert(self.base,self.out,update=self.update)
    def test_the_real_nstool_header_is_parsed(self):
        info=sx.parse_nstool_info(['[NCA Header]','  Content Type:    Program','  Key Generation:  3','  Size:            0x3ae96c00','  ProgID:          0x01007ef00011e000','  RightsId:        01007EF00011E8000000000000000003'])
        self.assertEqual((info['type'],info['title_id'],info['size'],info['rights_id']),('Program','01007ef00011e000',0x3ae96c00,'01007ef00011e8000000000000000003'))

class NstoolDownloadTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def archive(self,directory,name='nstool'):
        import zipfile
        path=pathlib.Path(directory)/'n.zip'
        with zipfile.ZipFile(path,'w') as bundle:bundle.writestr(name,'#!/bin/sh\necho "NSTool v1.9.2 (C) jakcron"\n')
        return path
    def test_the_download_must_match_the_pinned_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            made=self.archive(d)
            with self.assertRaisesRegex(ValueError,'SHA-256'):sx.fetch_nstool(self.store,fetch=lambda url,target,**kw:shutil.copy(made,target))
        self.assertFalse(sx.nstool_folder(self.store).exists())
    def test_a_verified_archive_leaves_only_the_executable(self):
        from deck_library import ports
        with tempfile.TemporaryDirectory() as d:
            made=self.archive(d)
            with patch.dict(sx.NSTOOL,{'sha256':ports.sha256_file(made)}):path=sx.fetch_nstool(self.store,fetch=lambda url,target,**kw:shutil.copy(made,target))
        self.assertEqual(path,str(sx.nstool_folder(self.store)/'nstool'));self.assertEqual(sx.tool_path(self.store),path);self.assertEqual(sorted(p.name for p in sx.nstool_folder(self.store).iterdir()),['build.json','nstool'])
    def test_an_archive_without_the_executable_is_refused(self):
        from deck_library import ports
        with tempfile.TemporaryDirectory() as d:
            made=self.archive(d,'other')
            with patch.dict(sx.NSTOOL,{'sha256':ports.sha256_file(made)}),self.assertRaisesRegex(ValueError,'forma esperada'):sx.fetch_nstool(self.store,fetch=lambda url,target,**kw:shutil.copy(made,target))

class ToolBuildTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def archive(self,directory):
        source=pathlib.Path(directory)/'src';source.mkdir();(source/'Makefile').write_text('all:\n');(source/'config.mk.template').write_text('')
        path=pathlib.Path(directory)/'h.tar.gz'
        with tarfile.open(path,'w:gz') as tar:tar.add(source,arcname='hactool-x')
        return path
    def test_the_download_must_match_the_pinned_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            made=self.archive(d)
            def fetch(url,target,**kw):shutil.copy(made,target)
            with patch('shutil.which',return_value='/usr/bin/x'),self.assertRaisesRegex(ValueError,'SHA-256'):sx.build_tool(self.store,fetch=fetch,run=lambda *a,**k:0)
    def test_a_verified_source_is_compiled_and_the_result_must_answer_as_hactool(self):
        from deck_library import ports
        with tempfile.TemporaryDirectory() as d:
            made=self.archive(d)
            def fetch(url,target,**kw):shutil.copy(made,target)
            def run(command,cwd=None,**kw):
                binary=pathlib.Path(cwd)/'hactool';binary.write_text('#!/bin/sh\necho "hactool (c) SciresM."\n');binary.chmod(0o755);return 0
            with patch('shutil.which',return_value='/usr/bin/x'),patch.dict(sx.HACTOOL,{'sha256':ports.sha256_file(made)}):
                path=sx.build_tool(self.store,fetch=fetch,run=run)
            self.assertEqual(path,str(sx.tool_folder(self.store)/'hactool'));self.assertEqual(sx.tool_path(self.store),path)
            self.assertEqual(sx.tool_path(Store(self.temp.name+'/none')),sx.tool_path(Store(self.temp.name+'/none')))

def pfs0(files):
    names=b''.join(n.encode()+b'\0' for n,_ in files);entries=b'';offset=0;position=0
    for name,data in files:
        entries+=struct.pack('<QQII',offset,len(data),position,0);offset+=len(data);position+=len(name.encode())+1
    return b'PFS0'+struct.pack('<III',len(files),len(names),0)+entries+names+b''.join(d for _,d in files)

@unittest.skipUnless(os.environ.get('DECK_LIBRARY_HACTOOL') and os.access(os.environ.get('DECK_LIBRARY_HACTOOL',''),os.X_OK),'set DECK_LIBRARY_HACTOOL to a real hactool binary')
class RealHactoolTests(unittest.TestCase):
    """Container handling against the real tool. NCA decryption needs a real dump and is not covered here."""
    def test_the_real_tool_is_recognised_and_unpacks_a_pfs0_with_its_ticket(self):
        tool=os.environ['DECK_LIBRARY_HACTOOL'];self.assertTrue(sx.is_hactool(tool))
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);keys=root/'prod.keys';keys.write_text(KEYS)
            package=root/'game.nsp';package.write_bytes(pfs0([('a.nca',b'nca-bytes'),('a.tik',ticket(RIGHTS_BASE,'11'*16))]))
            job=sx.Job(tool,keys,progress=lambda text:None);job.work=root;job.home=root/'home';job.home.mkdir()
            archives=job.unpack(package,0);self.assertEqual([p.name for p in archives],['a.nca']);self.assertEqual(job.titlekeys,{RIGHTS_BASE:'11'*16})

if __name__=='__main__':unittest.main()
