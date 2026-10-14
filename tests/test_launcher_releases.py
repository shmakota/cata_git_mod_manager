import importlib
import unittest
from unittest.mock import Mock, patch


# Importing the launcher normally reads/writes the user's configuration.
with patch("os.path.exists", return_value=True), patch(
    "builtins.open", unittest.mock.mock_open(read_data='{"game_install_dir": "."}')
):
    launcher = importlib.import_module("mod_manager.launcher")


class ReleaseSelectionTests(unittest.TestCase):
    def fetch(self, names, experimental=False, system="Windows", channel=None, pages=None):
        app = launcher.CataInstallerApp.__new__(launcher.CataInstallerApp)
        app.root = Mock()
        app.dropdown = unittest.mock.MagicMock()
        app.release_channel = Mock()
        app.release_channel.get.return_value = channel or ("Experimental" if experimental else "Nightly")
        app.selected_release = {"name": "previous selection"}
        release = {
            "name": "Test release",
            "prerelease": channel != "Stable",
            "assets": [
                {"name": name, "browser_download_url": "https://example.com/" + name}
                for name in names
            ],
        }
        response = Mock()
        response.links = {}
        response.json.return_value = release if experimental else [release]
        responses = []
        for index, page in enumerate(pages or []):
            page_response = Mock()
            page_response.json.return_value = page
            page_response.links = {"next": {"url": "https://example.com/page2"}} if index < len(pages) - 1 else {}
            responses.append(page_response)
        with patch.object(launcher.requests, "get", side_effect=responses or [response]) as get, patch.object(
            launcher.platform, "system", return_value=system
        ), patch.object(launcher.messagebox, "showerror") as showerror:
            app.fetch_releases()
            showerror.assert_not_called()
            self.assertEqual(get.call_count, len(responses) or 1)
        return app

    def test_pdb_before_game_is_skipped_for_both_channels(self):
        for experimental in (False, True):
            for suffix in (".pdb.zip", "-pdb.zip", "_PDB.zip", ".pdb"):
                with self.subTest(experimental=experimental, suffix=suffix):
                    base = "cbn-windows-tiles-x64"
                    if experimental:
                        base += "-experimental"
                    playable = base + ".zip"
                    app = self.fetch([base + suffix, playable], experimental)
                    self.assertEqual(app.selected_release["asset"]["name"], playable)
                    self.assertEqual(len(app.releases), 1)

    def test_symbols_only_release_clears_previous_selection(self):
        app = self.fetch(["cbn-windows-tiles-x64.pdb.zip"])
        self.assertEqual(app.releases, [])
        self.assertIsNone(app.selected_release)
        app.dropdown.set.assert_called_with("No releases found")

    def test_linux_tiles_selection_still_works(self):
        playable = "cbn-linux-tiles-x64.tar.gz"
        app = self.fetch(["cbn-windows-tiles-x64.zip", playable], system="Linux")
        self.assertEqual(app.selected_release["asset"]["name"], playable)

    def test_channel_filter_still_applies(self):
        normal = "cbn-windows-tiles-x64.zip"
        experimental = "cbn-windows-tiles-x64-experimental.zip"
        for enabled, expected in ((False, normal), (True, experimental)):
            with self.subTest(experimental=enabled):
                app = self.fetch([experimental, normal], experimental=enabled)
                self.assertEqual(app.selected_release["asset"]["name"], expected)

    def test_stable_skips_pdb_archive(self):
        playable = "cbn-windows-tiles-x64-msvc-v0.13.0.zip"
        app = self.fetch([
            "cbn-windows-tiles-x64-msvc-v0.13.0-pdb.zip", playable
        ], channel="Stable")
        self.assertEqual(app.selected_release["asset"]["name"], playable)

    def test_stable_follows_pagination_and_excludes_other_channels(self):
        asset = {"name": "cbn-windows-tiles-x64.zip", "browser_download_url": "https://example.com/game.zip"}
        nightly = {"name": "Nightly", "prerelease": True, "assets": [asset]}
        stable = {"name": "Stable v0.13.0", "prerelease": False, "assets": [asset]}
        older = dict(stable, name="Stable v0.12.0")
        draft = dict(stable, name="Draft", draft=True)
        experimental = dict(stable, name="Experimental", tag_name="experimental")
        app = self.fetch([], channel="Stable", pages=[
            [nightly, draft, experimental], [stable, older]
        ])
        self.assertEqual([r["name"] for r in app.releases], [stable["name"], older["name"]])

    def test_nightly_excludes_stable_releases(self):
        asset = {"name": "cbn-windows-tiles-x64.zip"}
        app = self.fetch([], pages=[[
            {"name": "Stable", "prerelease": False, "assets": [asset]},
            {"name": "Nightly", "prerelease": True, "assets": [asset]},
        ]])
        self.assertEqual([r["name"] for r in app.releases], ["Nightly"])


if __name__ == "__main__":
    unittest.main()
