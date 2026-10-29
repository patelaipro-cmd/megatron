import importlib.util
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("git"), "git absent")
class SynchroGitDivergenceTests(unittest.TestCase):
    def test_union_of_divergent_branches_is_refused(self):
        spec = importlib.util.spec_from_file_location("synchro_git", ROOT / "scripts" / "synchro_git.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rapport = mod.etape_divergence()
        self.assertTrue(all(rapport["checks"].values()), rapport)
