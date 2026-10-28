import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[1]

class InstallSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = dict(os.environ, HOME=str(self.home))

    def install(self):
        return subprocess.run([str(ROOT / 'install.sh')], cwd=ROOT, env=self.env,
                              text=True, capture_output=True)

    def test_modified_service_is_not_overwritten(self):
        unit = self.home / '.config/systemd/user/omarchy-dualsense.service'
        unit.parent.mkdir(parents=True)
        unit.write_text('custom unit\n')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to overwrite a modified service', result.stderr)
        self.assertEqual(unit.read_text(), 'custom unit\n')
        self.assertFalse((self.home / '.local/share/omarchy-dualsense').exists())

    def test_existing_plugin_files_are_not_overwritten(self):
        manifest = self.home / '.config/omarchy/plugins/io.github.robertg761.dualsense/manifest.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text('custom plugin\n')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to overwrite an existing plugin file', result.stderr)
        self.assertEqual(manifest.read_text(), 'custom plugin\n')
        self.assertFalse((self.home / '.local/share/omarchy-dualsense').exists())

if __name__ == '__main__': unittest.main()
