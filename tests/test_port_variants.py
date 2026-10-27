import json,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import port_variants as variants,ports,validated_games,broken_bond
from deck_library.models import Entry

class PortVariantTests(unittest.TestCase):
    def setUp(self):
        self.good=ports.clean({'repository':broken_bond.COMPATIBLE,'release_version':'v2.5'})
        self.old=ports.clean({'repository':broken_bond.ORIGINAL,'release_version':'v0.1.0-beta'})
        self.index=variants.Index([self.good,self.old])
    def test_validation_is_bound_to_repository_and_exact_version_including_prereleases(self):
        self.assertEqual(self.index.assess(self.good)['state'],'verified')
        for tag in ('v2.0','v2.6','2.5-beta','',None):
            state=self.index.assess({**self.good,'release_version':tag})
            self.assertNotEqual(state['state'],'verified');self.assertNotEqual(state['tone'],'green')
        rise=ports.clean({'repository':'jorjbarbosa/naruto-rise-recomp','release_version':'0.3.0'})
        self.assertNotEqual(variants.Index([rise]).assess(rise)['state'],'verified')
    def test_installed_hash_verified_linux_or_reviewed_metadata_do_not_grant_gameplay_validation(self):
        for tag in ('2.5','999',''):
            item={**self.old,'release_version':tag,'verified':True,'configured':True,'supported_os':['linux'],'score':100,'source':'Recomendado'}
            state=self.index.assess(item)
            self.assertEqual(state['state'],'other-variant');self.assertNotEqual(state['tone'],'green')
            self.assertEqual(state['report']['repository'],broken_bond.COMPATIBLE)
    def test_known_issue_applies_only_to_the_observed_revision_and_links_to_the_tested_variant(self):
        result=self.index.assess(self.old);self.assertEqual(result['state'],'issue');self.assertEqual(result['tone'],'red')
        self.assertIn('Pantalla negra',result['issue']);self.assertEqual(result['report']['version'],'2.5')
        self.assertEqual(self.index.assess(self.old,'0.2.0')['state'],'other-variant')
    def test_unvalidated_black_variants_are_grouped_without_a_winner(self):
        index=variants.Index();item=index.items['tgp482/black-xberecomp']
        family=[item,*index.alternatives(item)];self.assertEqual(len(family),4)
        for candidate in family:
            result=index.assess(candidate);self.assertEqual(result['state'],'unvalidated');self.assertIsNone(result['report'])
    def test_inference_requires_an_explicit_game_and_source_platform_and_keeps_sequels_separate(self):
        items=[ports.clean({'repository':f'owner/{n}','name':'Similar project','game_title':title,'category':platform}) for n,title,platform in [('a','Game','Xbox'),('b','Game','Xbox'),('c','Game 2','Xbox'),('d','Game','PlayStation 2'),('e','','Xbox'),('f','Game','')]]
        index=variants.Index(items,reports=[],families=[])
        self.assertEqual([i['repository'] for i in index.alternatives(items[0])],['owner/b'])
        self.assertFalse(index.alternatives(items[-1]));self.assertFalse(index.alternatives(items[-2]))
    def test_new_explicit_variant_can_join_a_curated_family_without_inheriting_its_report(self):
        item=ports.clean({'repository':'another/bond','game_title':'Naruto: The Broken Bond','category':'Xbox 360'})
        index=variants.Index([item]);self.assertEqual(len(index.alternatives(item)),2)
        self.assertEqual(index.assess(item)['state'],'other-variant')
    def test_installed_original_is_reported_as_another_variant_and_retains_its_own_version(self):
        entry=Entry('Broken Bond',['/bin/true'],metadata={'port_repository':broken_bond.ORIGINAL,'port_tag':'0.1.0-beta'})
        index=variants.Index([self.good],entries=[entry]);self.assertEqual(index.installed(self.good,[entry]),[entry])
        self.assertEqual(index.assess(variants.entry_item(entry))['state'],'issue')
        self.assertEqual(index.assess(self.good)['state'],'verified')
    def test_validated_games_never_open_a_different_port_with_the_same_game_id(self):
        report=next(r for r in validated_games.catalog() if r['id']=='broken-bond-v25')
        entry=Entry('Naruto',['/bin/true'],game_id=report['game_id'],metadata={'port_repository':broken_bond.ORIGINAL})
        with patch('deck_library.presets.public_game_id',return_value=report['game_id']),patch('deck_library.presets.adapter_for',return_value='instructions'):
            self.assertIsNone(validated_games.matching(report,[entry]))
    def test_external_variant_is_identified_without_offering_a_managed_migration(self):
        from deck_library import discovery,broken_bond
        from deck_library.models import Store
        with tempfile.TemporaryDirectory() as tmp:
            home=pathlib.Path(tmp);root=home/'ports/quiver-launcher';folder=root/'Apps/NarutoPort';folder.mkdir(parents=True)
            executable=folder/'game.AppImage';executable.write_text('fixture');executable.chmod(0o755)
            (folder/'selected_executable.txt').write_text(str(executable));(folder/'version.txt').write_text('v0.1.0-beta')
            (root/'apps.json').write_text(json.dumps({'apps':[{'folderName':'NarutoPort','repository':broken_bond.ORIGINAL,'name':'Naruto','category':'Xbox 360'}]}))
            entry=next(e for e in discovery.scan(home) if e.source==str(executable))
            self.assertEqual(entry.metadata['port_repository'],broken_bond.ORIGINAL);self.assertEqual(entry.metadata['port_tag'],'v0.1.0-beta')
            self.assertEqual(broken_bond.status(entry,Store(home/'private')),'')
            index=variants.Index(entries=[entry]);self.assertEqual(index.assess(variants.entry_item(entry))['state'],'issue')
            self.assertEqual(len(index.installed(index.items[broken_bond.COMPATIBLE.casefold()],[entry])),1)

    def test_duplicate_repositories_are_rejected_and_bundled_groups_have_no_empty_members(self):
        groups=variants.groups();self.assertTrue(all(g['repositories'] for g in groups))
        groups.append(groups[0])
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/'groups.json';path.write_text(json.dumps({'schema_version':1,'groups':groups}))
            with self.assertRaises(ValueError):variants.groups(path)
