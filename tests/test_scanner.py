from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from emptysearcher.scanner import FolderScanner


class FolderScannerTests(unittest.TestCase):
    def test_returns_empty_descendants_even_when_root_has_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.txt").write_text("content", encoding="utf-8")
            (root / "empty-a").mkdir()
            (root / "nested").mkdir()
            (root / "nested" / "empty-b").mkdir(parents=True)

            result = FolderScanner(
                root=root,
                ignored_file_patterns=[],
                ignored_dir_patterns=[],
                excluded_patterns=[],
            ).scan()

            paths = {node.relative_path for node in result.roots}
            self.assertEqual(paths, {"empty-a", "nested/empty-b"})

    def test_root_is_candidate_when_only_ignored_content_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Thumbs.db").write_text("", encoding="utf-8")
            (root / "cache").mkdir()

            result = FolderScanner(
                root=root,
                ignored_file_patterns=["Thumbs.db"],
                ignored_dir_patterns=["cache"],
                excluded_patterns=[],
            ).scan()

            self.assertEqual(len(result.roots), 1)
            self.assertEqual(result.roots[0].relative_path, ".")
            self.assertEqual(result.roots[0].ignored_files, ["Thumbs.db"])
            self.assertEqual(result.roots[0].ignored_dirs, ["cache"])

    def test_reports_progress_and_allows_cancellation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(5):
                (root / f"dir-{index}").mkdir()

            progress_events: list[tuple[int, int]] = []
            cancel_state = {"value": False}

            def on_progress(progress) -> None:
                progress_events.append((progress.scanned_directories, progress.total_directories))
                if progress.total_directories >= 3:
                    cancel_state["value"] = True

            result = FolderScanner(
                root=root,
                ignored_file_patterns=[],
                ignored_dir_patterns=[],
                excluded_patterns=[],
                progress_callback=on_progress,
                cancel_requested=lambda: cancel_state["value"],
            ).scan()

            self.assertTrue(result.cancelled)
            self.assertTrue(progress_events)
            self.assertGreaterEqual(progress_events[-1][1], 3)


if __name__ == "__main__":
    unittest.main()
