import unittest
from deck_library.port_requirements import original_requirement

class OriginalRequirementTests(unittest.TestCase):
    def test_builtin_disc_serial_and_revision_are_shown_exactly(self):
        a=original_requirement({'repository':'alexbeavs-ps1-ports/spider-man-recomp'})
        b=original_requirement({'repository':'alexbeavs-ps1-ports/spider-man-2-enter-electro-recomp'})
        self.assertEqual(a['label'],'SLUS-00875');self.assertTrue(a['known']);self.assertIn('SLUS-01378',b['label']);self.assertIn('Rev 1',b['label'])
    def test_wii_switch_and_ps4_requirements_keep_their_own_identifiers(self):
        for repo,label in [('patchzyy/Wiicompiled','RMCP01'),('hayatog/iss_pc','CUSA00223'),('K0NL/B2recomp','1.2'),('Revivedx/SavageWindRecomp','1.9.0')]:
            with self.subTest(repo=repo):self.assertIn(label,original_requirement({'repository':repo})['label'])
    def test_unreviewed_catalog_metadata_does_not_become_a_confirmed_requirement(self):
        result=original_requirement({'repository':'someone/port','disc':{'serial':'SLES-99999'},'name':'Spider-Man','note':'USA Rev 1'})
        self.assertEqual(result['label'],'ROM por confirmar');self.assertFalse(result['known']);self.assertEqual(result['source'],'https://github.com/someone/port')
    def test_title_id_is_distinguished_from_a_disc_revision(self):
        r=original_requirement({'repository':'florinp93/hells-gate-recomp'});self.assertIn('454108CF',r['label']);self.assertIn('no garantiza',r['details'])
