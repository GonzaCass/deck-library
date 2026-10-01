import json,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import cover_provider as covers
from deck_library.models import Entry,Store

class CoverProviderTests(unittest.TestCase):
    def test_aliases_preserve_game_identity_without_paths(self):
        entry=Entry('Mario Kart 8 Deluxe v3.0.3',['/private/path'],platform='Switch',game_id='0100152000022000')
        self.assertEqual(covers.title_for(entry),'Mario Kart 8 Deluxe')
        self.assertNotIn('private',covers.title_for(entry))
    def test_auto_match_refuses_unrelated_search_results(self):
        entry=Entry('Mario Kart Wii',['/bin/true'])
        self.assertIsNone(covers.best_match(entry,[{'title':'Mario Kart 8','url':'https://example.org/a.png'}]))
        row={'title':'Mario Kart Wii','url':'https://example.org/a.png'}
        self.assertEqual(covers.best_match(entry,[row]),row)
    def test_automatic_provider_falls_back_without_exposing_key(self):
        with patch.object(covers,'sgdb_search',side_effect=OSError('offline')),patch.object(covers,'libretro_search',return_value=[]),patch.object(covers,'wiki_search',return_value=[{'title':'Game'}]) as wiki:
            self.assertEqual(covers.search('Game',{'artwork_provider':'automatic','steamgriddb_key':'secret'}),[{'title':'Game'}]);wiki.assert_called_once_with('Game')
    def test_https_and_explicit_key_required(self):
        with self.assertRaises(ValueError):covers.request('http://example.org')
        with self.assertRaises(ValueError):covers.sgdb_search('Game','')
        with patch.object(covers,'wiki_search') as wiki:
            self.assertEqual(covers.search('Game',{'artwork_provider':'off'}),[]);wiki.assert_not_called()
    def test_download_validates_images_and_keeps_origin_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);row={'title':'Game','url':'https://example.org/cover.png','page':'https://example.org/game','provider':'Example'}
            with patch.object(covers,'request',return_value=b'<html>error</html>'):
                with self.assertRaises(ValueError):covers.download(row,store)
            with patch.object(covers,'request',return_value=b'\x89PNG\r\n\x1a\nfixture'):
                path=pathlib.Path(covers.download(row,store));self.assertTrue(path.is_relative_to(store.root));self.assertEqual(json.loads(path.with_suffix('.json').read_text())['provider'],'Example')

    def test_libretro_matches_title_and_prefers_europe_without_partial_matches(self):
        covers.libretro_index.cache_clear()
        body=b'<a href="Mario%20Kart%20Wii%20(USA).png">x</a><a href="Mario%20Kart%20Wii%20(Europe).png">x</a><a href="Kustom%20Mario%20Kart%20Wii.png">x</a><a href="../escape.png">x</a>'
        with patch.object(covers,'request',return_value=body):
            rows=covers.libretro_search('Mario Kart Wii','WiiCompiled');self.assertEqual(len(rows),2);self.assertIn('(Europe)',rows[0]['title']);self.assertTrue(all(row['url'].startswith('https://thumbnails.libretro.com/') for row in rows))
        covers.libretro_index.cache_clear()

    def test_steamgriddb_requests_portraits_and_filters_sensitive_results(self):
        games={'data':[{'id':7,'name':'Game'}]}
        grids={'data':[{'id':1,'url':'https://cdn.example.org/1.png','width':600,'height':900},{'id':2,'url':'https://cdn.example.org/2.png','nsfw':True},{'id':3,'url':'https://cdn.example.org/3.png','humor':True}]}
        with patch.object(covers,'request',side_effect=[json.dumps(games).encode(),json.dumps(grids).encode()]) as request:
            rows=covers.sgdb_search('Game','private-api-key');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['height'],900);self.assertIn('dimensions=600x900',request.call_args_list[1].args[0]);self.assertNotIn('private-api-key',json.dumps(rows))
