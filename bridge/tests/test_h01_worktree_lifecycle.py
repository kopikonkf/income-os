import subprocess
import tempfile
import unittest
from pathlib import Path

from bin import die_h01_worktree as wt


def run(*args, cwd=None):
    return subprocess.run([*args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def make_remote(root: Path) -> Path:
    source, remote = root / "source", root / "remote.git"
    source.mkdir()
    run("git", "init", "-b", "main", cwd=source)
    run("git", "config", "user.name", "H01 Test", cwd=source)
    run("git", "config", "user.email", "h01@example.invalid", cwd=source)
    (source / "README.md").write_text("one\n", encoding="utf-8")
    run("git", "add", "README.md", cwd=source)
    run("git", "commit", "-m", "seed", cwd=source)
    run("git", "init", "--bare", str(remote))
    run("git", "remote", "add", "origin", str(remote), cwd=source)
    run("git", "push", "-u", "origin", "main", cwd=source)
    return remote


class H01WorktreeLifecycleTests(unittest.TestCase):
    def test_guard_rejects_live_srv_die(self):
        with self.assertRaisesRegex(wt.LifecycleError, "E_PROTECTED_LIVE_PATH"):
            wt.assert_engineering_path("/srv/die/company", "/home/kopiko/die-sessions")

    def test_guard_rejects_outside_session_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(wt.LifecycleError, "E_OUTSIDE_ENGINEERING_WORKTREE"):
                wt.assert_engineering_path(root / "other" / "H01-003", root / "sessions")

    def test_create_current_origin_main_then_close_removes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); remote = make_remote(root)
            anchor, sessions, states = root / "state" / "income-os.git", root / "sessions", root / "states"
            created = wt.create_worktree("H01-TEST", anchor, sessions, states, str(remote))
            target = sessions / "H01-TEST"
            remote_main = run("git", "--git-dir", str(remote), "rev-parse", "refs/heads/main").stdout.strip()
            self.assertEqual(created["base_sha"], remote_main)
            self.assertEqual(run("git", "-C", str(target), "rev-parse", "HEAD").stdout.strip(), remote_main)
            closed = wt.close_worktree("H01-TEST", sessions, states)
            self.assertEqual(closed["status"], "CLOSED")
            self.assertFalse(target.exists())
            self.assertTrue(any(ref.endswith("/main") for ref in closed["published_refs"]))

    def test_close_refuses_dirty_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); remote = make_remote(root)
            anchor, sessions, states = root / "state" / "income-os.git", root / "sessions", root / "states"
            wt.create_worktree("H01-DIRTY", anchor, sessions, states, str(remote))
            target = sessions / "H01-DIRTY"
            (target / "dirty.txt").write_text("keep me\n", encoding="utf-8")
            with self.assertRaisesRegex(wt.LifecycleError, "E_WORKTREE_DIRTY"):
                wt.close_worktree("H01-DIRTY", sessions, states)
            self.assertTrue(target.exists())

    def test_create_refuses_existing_state_without_materializing_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); remote = make_remote(root)
            anchor, sessions, states = root / "state" / "income-os.git", root / "sessions", root / "states"
            states.mkdir(parents=True)
            (states / "H01-STALE.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(wt.LifecycleError, "E_SESSION_STATE_EXISTS"):
                wt.create_worktree("H01-STALE", anchor, sessions, states, str(remote))
            self.assertFalse((sessions / "H01-STALE").exists())

    def test_close_refuses_unpublished_head(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); remote = make_remote(root)
            anchor, sessions, states = root / "state" / "income-os.git", root / "sessions", root / "states"
            wt.create_worktree("H01-UNPUBLISHED", anchor, sessions, states, str(remote))
            target = sessions / "H01-UNPUBLISHED"
            run("git", "config", "user.name", "H01 Test", cwd=target)
            run("git", "config", "user.email", "h01@example.invalid", cwd=target)
            (target / "README.md").write_text("two\n", encoding="utf-8")
            run("git", "add", "README.md", cwd=target)
            run("git", "commit", "-m", "local-only", cwd=target)
            with self.assertRaisesRegex(wt.LifecycleError, "E_UNPUBLISHED_HEAD"):
                wt.close_worktree("H01-UNPUBLISHED", sessions, states)
            self.assertTrue(target.exists())

    def test_state_root_under_live_srv_die_is_rejected(self):
        with self.assertRaisesRegex(wt.LifecycleError, "E_PROTECTED_LIVE_PATH"):
            wt.state_path("/srv/die/.engineering-state", "H01-003")


if __name__ == "__main__":
    unittest.main()
