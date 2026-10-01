import pathlib,tempfile,unittest,struct
from deck_library.models import Entry
from deck_library.steam import write_kv,read_kv,get,update_shortcuts,SteamRunningError
from deck_library.steam_inventory import merge_steam,sync_covers
from deck_library.steam_input import parse_text,bindings,local_profiles
from deck_library.discovery import scan
class SteamIntegrationTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.account=self.root/'Steam/userdata/1/config';self.account.mkdir(parents=True)
 def tearDown(self):self.tmp.cleanup()
 def fixture(self):
  item={'appname':(1,'Old Minecraft'),'exe':(1,'"flatpak"'),'LaunchOptions':(1,'run org.prismlauncher.PrismLauncher --launch "instance-id"'),'StartDir':(1,'"/games"'),'appid':(2,struct.pack('<I',0xf0012345)),'AllowDesktopConfig':(2,struct.pack('<I',1)),'tags':(0,{'0':(1,'Favorite')})}
  (self.account/'shortcuts.vdf').write_bytes(write_kv({'shortcuts':(0,{'0':(0,item)})}));return item
 def test_import_links_prism_instance_without_duplicate_or_identity_change(self):
  self.fixture();entry=Entry('New instance name',['/bin/true'],platform='Minecraft',metadata={'instance_id':'instance-id'})
  found=merge_steam([entry],account=self.account);self.assertEqual(len(found),1);self.assertEqual(found[0].id,entry.id);self.assertEqual(found[0].metadata['steam_appid'],0xf0012345)
 def test_edit_imported_shortcut_preserves_id_launch_options_controls_and_tags(self):
  old=self.fixture();entry=merge_steam([],account=self.account)[0];entry.name='Renamed'
  update_shortcuts(self.account,[entry],lambda e:pathlib.Path(e.command[0]),lambda:False)
  saved=read_kv((self.account/'shortcuts.vdf').read_bytes())['shortcuts'][1]['0'][1]
  for key in ('appid','exe','LaunchOptions','StartDir','AllowDesktopConfig','tags'):self.assertEqual(saved[key],old[key])
  self.assertEqual(get(saved,'appname'),'Renamed')
 def test_cover_replacement_has_backup_and_refuses_live_steam(self):
  entry=Entry('Game',['/bin/true']);cover=self.root/'art.png';cover.write_bytes(b'\x89PNG\r\n\x1a\nfixture');entry.cover=str(cover);grid=self.account/'grid';grid.mkdir();old=grid/'123p.jpg';old.write_bytes(b'old')
  with self.assertRaises(SteamRunningError):sync_covers(self.account,[entry],[{'id':entry.id,'appid':123}],lambda:True)
  self.assertEqual(old.read_bytes(),b'old')
  self.assertEqual(sync_covers(self.account,[entry],[{'id':entry.id,'appid':123}],lambda:False),1);self.assertFalse(old.exists());self.assertEqual((grid/'123p.png').read_bytes(),cover.read_bytes());self.assertEqual(next((grid/'.deck-library-backups').iterdir()).read_bytes(),b'old')
 def test_repeated_steam_input_groups_are_preserved_and_account_data_not_in_summary(self):
  text='"controller_mappings" { "creator" "PRIVATE" "group" { "inputs" { "button_a" { "binding" "key_press SPACE, , " } } } "group" { "inputs" { "button_b" { "binding" "key_press ESCAPE, , " } } } }'
  rows=bindings(parse_text(text));self.assertEqual(len(rows),2);self.assertNotIn('PRIVATE',str(rows))
 def test_new_quiver_port_in_custom_appspath_is_discovered(self):
  import json
  quiver=self.root/'ports/quiver-launcher';quiver.mkdir(parents=True);apps=self.root/'custom ports';port=apps/'Example-Port';port.mkdir(parents=True);exe=port/'run.sh';exe.write_text('#!/bin/sh');exe.chmod(0o755);(port/'selected_executable.txt').write_text('run.sh');(quiver/'settings.json').write_text(json.dumps({'AppsPath':str(apps)}))
  self.assertTrue(any(e.source==str(exe) for e in scan(self.root)))

 def test_fresh_quiver_port_without_saved_selection_is_detected_if_unambiguous(self):
  apps=self.root/'ports/quiver-launcher/Apps/New-Port';apps.mkdir(parents=True);game=apps/'Game.AppImage';game.write_bytes(b'ELF');(apps/'Setup.AppImage').write_bytes(b'SETUP')
  self.assertTrue(any(e.source==str(game) for e in scan(self.root)))
