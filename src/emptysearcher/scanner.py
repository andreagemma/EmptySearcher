from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path


@dataclass
class CandidateNode:
    path: Path
    relative_path: str
    ignored_files: list[str] = field(default_factory=list)
    ignored_dirs: list[str] = field(default_factory=list)
    children: list["CandidateNode"] = field(default_factory=list)


@dataclass
class ScanResult:
    roots: list[CandidateNode] = field(default_factory=list)
    scanned_directories: int = 0
    cancelled: bool = False


@dataclass
class ScanProgress:
    scanned_directories: int
    total_directories: int
    current_path: str


@dataclass
class _WalkNode:
    candidates: list[CandidateNode]
    counts_as_content: bool


class _ScanCancelled(Exception):
    """Raised when a scan is cancelled by the caller."""


class FolderScanner:
    def __init__(
        self,
        root: Path,
        ignored_file_patterns: list[str],
        ignored_dir_patterns: list[str],
        excluded_patterns: list[str],
        progress_callback: Callable[[ScanProgress], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> None:
        self.root = root
        self.ignored_file_patterns = ignored_file_patterns
        self.ignored_dir_patterns = ignored_dir_patterns
        self.excluded_patterns = excluded_patterns
        self.progress_callback = progress_callback
        self.cancel_requested = cancel_requested or (lambda: False)
        self._discovered_directories = 0
        self._scanned_directories = 0

    def scan(self) -> ScanResult:
        if not self.root.exists() or not self.root.is_dir():
            return ScanResult()

        self._discovered_directories = 1
        self._scanned_directories = 0
        self._emit_progress(self.root)

        try:
            walk = self._scan_dir(self.root)
        except _ScanCancelled:
            return ScanResult(scanned_directories=self._scanned_directories, cancelled=True)

        return ScanResult(roots=walk.candidates, scanned_directories=self._scanned_directories)

    def _scan_dir(self, path: Path) -> _WalkNode:
        self._check_cancel()
        relative_path = self._relative_path(path)
        path_name = path.name or str(path)

        if path != self.root and self._matches_patterns(path_name, relative_path, self.excluded_patterns):
            return _WalkNode(candidates=[], counts_as_content=True)

        if path != self.root and self._matches_patterns(path_name, relative_path, self.ignored_dir_patterns):
            return _WalkNode(candidates=[], counts_as_content=False)

        descendant_candidates: list[CandidateNode] = []
        contains_content = False
        ignored_files: list[str] = []
        ignored_dirs: list[str] = []

        try:
            entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError:
            self._mark_directory_scanned(path)
            return _WalkNode(candidates=[], counts_as_content=True)

        for entry in entries:
            self._check_cancel()
            if entry.is_symlink():
                contains_content = True
                continue

            if entry.is_dir():
                child_relative = self._relative_path(entry)
                child_name = entry.name

                if self._matches_patterns(child_name, child_relative, self.excluded_patterns):
                    contains_content = True
                    continue

                if self._matches_patterns(child_name, child_relative, self.ignored_dir_patterns):
                    ignored_dirs.append(child_name)
                    continue

                self._discovered_directories += 1
                self._emit_progress(entry)
                child = self._scan_dir(entry)

                descendant_candidates.extend(child.candidates)
                if child.counts_as_content:
                    contains_content = True
            else:
                file_relative = self._relative_path(entry)
                if self._matches_patterns(entry.name, file_relative, self.ignored_file_patterns):
                    ignored_files.append(entry.name)
                else:
                    contains_content = True

        self._mark_directory_scanned(path)

        if contains_content:
            return _WalkNode(candidates=descendant_candidates, counts_as_content=True)

        node = CandidateNode(
            path=path,
            relative_path=relative_path,
            ignored_files=sorted(set(ignored_files)),
            ignored_dirs=sorted(set(ignored_dirs)),
            children=descendant_candidates,
        )
        return _WalkNode(candidates=[node], counts_as_content=False)

    def _relative_path(self, path: Path) -> str:
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return path.as_posix()
        return "." if not rel.parts else rel.as_posix()

    @staticmethod
    def _matches_patterns(name: str, relative_path: str, patterns: list[str]) -> bool:
        rel = relative_path.replace("\\", "/")
        basename = name.replace("\\", "/")
        for pattern in patterns:
            if fnmatch(basename, pattern) or fnmatch(rel, pattern):
                return True
        return False

    def _emit_progress(self, path: Path) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback(
            ScanProgress(
                scanned_directories=self._scanned_directories,
                total_directories=self._discovered_directories,
                current_path=str(path),
            )
        )

    def _mark_directory_scanned(self, path: Path) -> None:
        self._scanned_directories += 1
        self._emit_progress(path)

    def _check_cancel(self) -> None:
        if self.cancel_requested():
            raise _ScanCancelled()
