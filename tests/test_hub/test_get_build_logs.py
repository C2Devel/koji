import mock
import os
import shutil
import tempfile
import unittest

import koji
import kojihub


class TestGetBuildLogs(unittest.TestCase):

    def setUp(self):
        self.get_build = mock.patch('kojihub.get_build').start()
        self.pathinfo = mock.patch('koji.pathinfo').start()
        self.tempdir = tempfile.mkdtemp()
        koji.pathinfo.build_logs.return_value = self.tempdir

    def tearDown(self):
        mock.patch.stopall()
        shutil.rmtree(self.tempdir)

    def make_tree(self, data):
        for filepath in data:
            path = "%s/%s" % (self.tempdir, filepath)
            if path.endswith('/'):
                # just make a directory
                dirpath = path
                path = None
            else:
                dirpath = os.path.dirname(path)
            koji.ensuredir(dirpath)
            if path:
                with file(path, 'w') as fo:
                    fo.write('TEST LOG FILE CONTENTS\n')

    def test_get_build_logs_basic(self):
        files = [
                'noarch/build.log',
                'x86_64/build.log',
                's390x/build.log',
                ]
        files.sort()
        self.make_tree(files)
        data = kojihub.get_build_logs('fakebuild')
        files2 = ["%s/%s" % (f['dir'], f['name']) for f in data]
        files2.sort()
        self.assertEqual(files, files2)

    def test_get_build_logs_dir_missing(self):
        koji.pathinfo.build_logs.return_value = "%s/NOSUCHDIR" % self.tempdir
        data = kojihub.get_build_logs('fakebuild')
        self.assertEqual(data, [])

    def test_get_build_logs_notadir(self):
        fn = "%s/SOMEFILE" % self.tempdir
        with open(fn, 'w') as fo:
            fo.write('NOT A DIRECTORY\n')
        koji.pathinfo.build_logs.return_value = fn
        try:
            data = kojihub.get_build_logs('fakebuild')
            raise Exception('Expected exception not raised')
        except koji.GenericError as e:
            self.assertEqual(e.args[0][:15], 'Not a directory')

    def test_get_build_logs_emptydirs(self):
        files = [
                './build.log',
                'noarch/build.log',
                'noarch/root.log',
                'x86_64/build.log',
                's390x/build.log',
                'oddball/log/dir/fake.log',
                ]
        empty_dirs = [
                'foo/bar/baz/',
                'a/b/c/',
                'empty/',
                ]
        files.sort()
        self.make_tree(files + empty_dirs)
        data = kojihub.get_build_logs('fakebuild')
        files2 = ["%s/%s" % (f['dir'], f['name']) for f in data]
        files2.sort()
        self.assertEqual(files, files2)

    def test_get_build_logs_symlinks(self):
        # symlinks should be ignored
        files = [
                'noarch/build.log',
                'noarch/root.log',
                'noarch/mock.log',
                'noarch/checkout.log',
                'noarch/readme.txt',
                'oddball/log/dir/fake.log',
                ]
        empty_dirs = [
                'just_links/',
                ]
        files.sort()
        self.make_tree(files + empty_dirs)
        os.symlink('SOME/PATH', '%s/%s' % (self.tempdir, 'symlink.log'))
        os.symlink('SOME/PATH', '%s/%s' % (self.tempdir, 'just_links/foo.log'))
        os.symlink('SOME/PATH', '%s/%s' % (self.tempdir, 'just_links/bar.log'))
        data = kojihub.get_build_logs('fakebuild')
        files2 = ["%s/%s" % (f['dir'], f['name']) for f in data]
        files2.sort()
        self.assertEqual(files, files2)
