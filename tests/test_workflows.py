import json,pathlib,tempfile,unittest,urllib.error
from unittest.mock import patch
from deck_library.models import Store,Entry,atomic_json
from deck_library.service import pending_changes,cancel_pending,queue_entries,sync
from deck_library.conflicts import analyze
from deck_library.updates import release_notes,check_quiver

class WorkflowTests(unittest.TestCase):
    def test_pending_names_every_operation_and_can_cancel_without_steam_write(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);e=Entry('Deck Library',['/bin/true'],metadata={'library_app':True,'steam_appid':123});store.save([e]);atomic_json(store.root/'pending.json',{'ids':[e.id],'remove':[123],'controllers':[123],'art':[{'appid':123,'slot':'hero','file':'picture.png'}]})
            rows=pending_changes(store);self.assertEqual(len(rows),4);self.assertTrue(all('Deck Library' in r['description'] for r in rows));self.assertIn('instalación',rows[0]['detail'])
            with patch('deck_library.service.steam_running',return_value=True):self.assertTrue(cancel_pending(store))
            self.assertEqual(pending_changes(store),[]);self.assertTrue(store.path.exists())
    def test_cancelled_waiting_worker_exits_without_writing_steam(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);e=Entry('A',['/bin/true'])
            with patch('deck_library.service.steam_running',return_value=True):queue_entries([e],pathlib.Path(root)/'steam',store,start_worker=False)
            def stop(_):
                with patch('deck_library.service.steam_running',return_value=True):cancel_pending(store)
            with patch('deck_library.service.steam_running',side_effect=[True,False]),patch('deck_library.service.time.sleep',side_effect=stop),patch('deck_library.service.update_shortcuts') as write:
                self.assertEqual(sync(store)['state'],'idle');write.assert_not_called()
    def test_emudeck_wrapper_and_its_appimage_are_one_installation(self):
        with tempfile.TemporaryDirectory() as root:
            home=pathlib.Path(root);apps=home/'Applications';apps.mkdir();(apps/'eden.AppImage').write_bytes(b'\x7fELFtest');launchers=home/'Emulation/tools/launchers';launchers.mkdir(parents=True);wrapper=launchers/'eden.sh';wrapper.write_text('#!/bin/bash\nexec "$HOME/Applications/eden.AppImage" "$@"')
            with patch('deck_library.conflicts.shutil.which',return_value=None):self.assertEqual(analyze([],home,{'emulators':{'eden':[str(wrapper)]}}),[])
            (apps/'eden-other.AppImage').write_bytes(b'\x7fELFother')
            with patch('deck_library.conflicts.shutil.which',return_value=None):rows=analyze([],home)
            self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['paths']),2);self.assertNotIn(str(wrapper),rows[0]['paths'])
    def test_configured_appimage_and_symlink_are_not_counted_twice(self):
        with tempfile.TemporaryDirectory() as root:
            home=pathlib.Path(root);apps=home/'Applications';apps.mkdir();a=apps/'eden.AppImage';a.write_bytes(b'\x7fELFtest');b=apps/'eden-link.AppImage';b.symlink_to(a)
            with patch('deck_library.conflicts.shutil.which',return_value=None):self.assertEqual(analyze([],home,{'emulators':{'eden':[str(b)]}}),[])
    def test_release_notes_are_for_the_displayed_tag(self):
        calls=[]
        def get(url):calls.append(url);return {'tag_name':'v2.1','body':'Actualización del autor'}
        self.assertEqual(release_notes({'repository':'owner/repo','latest':'v2.1'},get),'Actualización del autor');self.assertIn('/releases/tags/v2.1',calls[0])
        self.assertEqual(release_notes({'repository':'owner/repo','latest':'v1.0'},get),'')
        self.assertEqual(release_notes({'notes':'Texto en caché'},lambda _:self.fail('Unexpected request')),'Texto en caché')
    def test_quiver_retains_publisher_release_notes(self):
        with patch('deck_library.updates.quiver_apps',return_value=[{'name':'Port','repository':'owner/repo','installed':'1.0','skipped':''}]):
            rows=check_quiver(get=lambda _:{'tag_name':'2.0','body':'Fixed controls','html_url':'https://github.com/owner/repo/releases/tag/2.0'})
        self.assertEqual(rows[0]['notes'],'Fixed controls')

    def test_release_markdown_is_displayed_without_remote_images_or_html(self):
        from deck_library.updates import notes_text
        text=notes_text('## Changes\n**Fixed** controls\n![image](https://example.org/img.png)\n<details><summary>More</summary>Details</details>')
        self.assertIn('Fixed controls',text);self.assertNotIn('<details>',text);self.assertNotIn('example.org',text)
