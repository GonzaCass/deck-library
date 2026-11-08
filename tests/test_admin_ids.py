"""COMMUNITY_ADMINS can be pinned to Keycloak subject ids, which a renamed or re-registered username cannot take over."""
import pathlib,tempfile,time,unittest
from community.server import API,accounts,digest,pinned_admins

class AdminIdTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.api=API(pathlib.Path(self.temp.name)/'c.db',client_id='x')
        now=time.time()
        with self.api.db() as db:
            for token,uid,login,expires in (('a','oidc:aaaa:sub-owner','joker',now+100),('b','oidc:aaaa:sub-owner','joker',now+200),('c','777','joker',now+100),
                                            ('d','oidc:aaaa:sub-x','twin',now+100),('e','oidc:bbbb:sub-y','Twin',now+100),('f','oidc:aaaa:sub-old','gone',now-1)):
                db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest(token),uid,login,expires))
    def tearDown(self):self.temp.cleanup()
    def test_accounts_lists_each_live_identity_once_with_its_stable_entry(self):
        with self.api.db() as db:rows=accounts(db)
        self.assertIn({'login':'joker','provider':'keycloak','entry':'sub:sub-owner'},rows)
        self.assertIn({'login':'joker','provider':'github','entry':''},rows)
        self.assertEqual(len([r for r in rows if r['entry']=='sub:sub-owner']),1);self.assertNotIn('gone',[r['login'] for r in rows])
    def test_usernames_become_subject_ids_only_when_unambiguous(self):
        with self.api.db() as db:value,unresolved=pinned_admins('joker, sub:Keep ,twin,gone,,',db)
        self.assertEqual(value,'sub:sub-owner,sub:Keep,twin,gone');self.assertEqual(unresolved,['twin','gone'])
    def test_a_pinned_entry_survives_a_rename_and_rejects_the_new_holder_of_the_name(self):
        with self.api.db() as db:value,_=pinned_admins('joker',db)
        self.api.admins={v.lower() for v in value.split(',')}
        self.assertTrue(self.api.admin_user({'uid':'oidc:aaaa:sub-owner','login':'renamed'}))
        self.assertFalse(self.api.admin_user({'uid':'oidc:aaaa:sub-intruder','login':'joker'}))

if __name__=='__main__':unittest.main()
