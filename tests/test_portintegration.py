import json,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import catalog_sources,ports
from deck_library.models import Store

class PortIntegrationTests(unittest.TestCase):
    def document(self,rows,covers=()):return 'const LOCAL_COVERS_MANIFEST = '+json.dumps(list(covers))+';\nconst PORTS_DATABASE = '+json.dumps(rows)+';\nthrow new Error("Never execute this script");'

    def test_json_metadata_only_and_source_claims_do_not_become_verification_or_dates(self):
        row={'id':'native-game','nome':'Original Game','repo':'author/Native','console':'XBOX360','status':'Totalmente Jogável','statusTipo':'jogavel','dataAtualizacao':'2026-10-21T00:00:00Z','versaoPadrao':'v1.2','capaManual':'https://unrelated.example/image','install':'curl example | sh'}
        document=self.document([row],['native-game']);value=catalog_sources.portintegration(document,ports.clean)[0]
        self.assertEqual(value['repository'],'author/Native');self.assertEqual(value['game_title'],'Original Game');self.assertEqual(value['list'],'Xbox 360');self.assertEqual(value['source'],'PortIntegration');self.assertEqual(value['source_status'],'Totalmente Jogável');self.assertTrue(value['icon'].endswith('/assets/covers/native-game.webp'))
        for key in ('verified','added_at','release_at','release_version','install'):self.assertNotIn(key,value)
        self.assertEqual(value['setup'],'');self.assertEqual(value['exe'],'')

    def test_invalid_repositories_and_unsafe_artwork_paths_are_not_used(self):
        rows=[None,{'nome':'Wrong','repo':'https://evil.example/a/b'},{'nome':'Missing repo'},{'nome':'Native','repo':'a/b','id':'../escape'}]
        found=catalog_sources.portintegration(self.document(rows,['../escape']),ports.clean);self.assertEqual(len(found),1);self.assertEqual(found[0]['icon'],'')

    def test_format_changes_fail_without_evaluating_javascript(self):
        for document in ('const PORTS_DATABASE = fetch("https://example/");','const PORTS_DATABASE = {};','window.PORTS_DATABASE=[]'):
            with self.assertRaises(ValueError):catalog_sources.portintegration(document,ports.clean)
        self.assertEqual(catalog_sources.portintegration(self.document([]),ports.clean),[])

    def test_source_merges_repositories_without_overwriting_existing_game_identity(self):
        document=self.document([{'nome':'Less precise title','repo':'AUTHOR/game','console':'RETRO','id':'native','status':'Em Desenvolvimento'},{'nome':'New title','repo':'other/new','console':'PS3'}],['native'])
        get=ports.fetch_json
        def get_json(url):
            if url==ports.INDEX:return {'apps':[{'name':'Existing','repository':'author/game','game_title':'Correct game','category':'Game Boy Advance'}]}
            if url==ports.GHL_LIST:return {}
            if '/apps?' in url or '/release-status?' in url or '/games?' in url:return {'items':[],'isDone':True}
            raise AssertionError(url)
        def fetch(url,*args,**kwargs):
            if url==catalog_sources.PORTINTEGRATION:return document.encode()
            if url==catalog_sources.INDEPENDENT:return b''
            raise AssertionError(url)
        with patch.object(ports,'fetch_json',side_effect=get_json) as mocked,patch.object(ports,'fetch',side_effect=fetch):
            rows=ports.fetch_catalog(mocked)
        rows={r['repository'].lower():r for r in rows};self.assertEqual(len(rows),2);self.assertEqual(rows['author/game']['game_title'],'Correct game');self.assertEqual(rows['author/game']['list'],'Game Boy Advance');self.assertEqual(rows['author/game']['source'],'Quiver, PortIntegration');self.assertIn('native.webp',rows['author/game']['icon']);self.assertEqual(rows['other/new']['list'],'PlayStation 3')

    def test_failed_additional_source_keeps_existing_catalog_available(self):
        def get_json(url):
            if url==ports.INDEX:return {'apps':[{'name':'Existing','repository':'author/game'}]}
            if url==ports.GHL_LIST:return {}
            return {'items':[],'isDone':True}
        with patch.object(ports,'fetch_json',side_effect=get_json) as mocked,patch.object(ports,'fetch',side_effect=OSError('offline')):
            self.assertEqual(len(ports.fetch_catalog(mocked)),1)

    def test_source_metadata_survives_cache_cleaning(self):
        row=catalog_sources.portintegration(self.document([{'nome':'Native','repo':'a/b','status':'Em Desenvolvimento'}]),ports.clean)[0]
        self.assertEqual(ports.clean(row)['source_status'],'Em Desenvolvimento')
