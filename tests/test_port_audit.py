import importlib.util,pathlib,unittest,urllib.error

spec=importlib.util.spec_from_file_location('audit_ports',pathlib.Path(__file__).resolve().parent.parent/'tools/audit_ports.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class PortAuditTests(unittest.TestCase):
    def test_audit_uses_the_actual_package_planner_for_each_runtime(self):
        for filename,status in [('Game-linux-x64.tar.gz','native'),('Game-win64.tar.xz','proton'),('Game.zip','inspect-archive'),('Game-arm64.apk','no-compatible-package')]:
            release={'tag_name':'v1','assets':[{'name':filename}]}
            row=audit.inspect({'repository':'owner/Game'},lambda _:release)
            self.assertEqual(row['status'],status);self.assertEqual(row.get('tag'),'v1')

    def test_dedicated_and_source_only_flows_are_not_marked_portable_games(self):
        def unexpected(_):raise AssertionError('Dedicated flows must not fetch generic releases')
        self.assertEqual(audit.inspect({'repository':'GenryTheFox0/Project-2099','setup':'project2099'},unexpected)['status'],'specialized')
        row=audit.inspect({'repository':'portingpete/Black-2006-Recomp'},lambda _:{'assets':[{'name':'BLACK-linux.zip'}]})
        self.assertEqual(row['status'],'manual-build')

    def test_missing_release_repository_and_network_errors_are_distinct(self):
        def no_releases(url):
            if url.endswith('/latest'):raise urllib.error.HTTPError(url,404,'Not found',{},None)
            return []
        self.assertEqual(audit.inspect({'repository':'owner/Game'},no_releases)['status'],'no-release')
        def unavailable(url):raise urllib.error.HTTPError(url,404,'Not found',{},None)
        self.assertEqual(audit.inspect({'repository':'owner/Game'},unavailable)['status'],'unavailable')
        def failed(_):raise OSError('private request detail')
        row=audit.inspect({'repository':'owner/Game'},failed)
        self.assertEqual(row['status'],'request-failed');self.assertNotIn('private',row['note'])

if __name__=='__main__':unittest.main()
