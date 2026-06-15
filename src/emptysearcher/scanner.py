from __future__ import annotations

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


@dataclass
class _WalkNode:
    candidate: CandidateNode | None
    counts_as_content: bool
    scanned_directories: int


class FolderScanner:
    def __init__(
        self,
        root: Path,
        ignored_file_patterns: list[str],
        ignored_dir_patterns: list[str],
        excluded_patterns: list[str],
    ) -> None:
        self.root = root
        self.ignored_file_patterns = ignored_file_patterns
        self.ignored_dir_patterns = ignored_dir_patterns
        self.excluded_patterns = excluded_patterns

    def scan(self) -> ScanResult:
        if not self.root.exists() or not self.root.is_dir():
            return ScanResult()

        walk = self._scan_dir(self.root)
        roots = [walk.candidate] if walk.candidate else []
        return ScanResult(roots=roots, scanned_directories=walk.scanned_directories)

    def _scan_dir(self, path: Path) -> _WalkNode:
        relative_path = self._relative_path(path)
        path_name = path.name or str(path)

        if path != self.root and self._matches_patterns(path_name, relative_path, self.excluded_patterns):
            return _WalkNode(candidate=None, counts_as_content=True, scanned_directories=0)

        if path != self.root and self._matches_patterns(path_name, relative_path, self.ignored_dir_patterns):
            node = CandidateNode(path=path, relative_path=relative_path)
            return _WalkNode(candidate=node, counts_as_content=False, scanned_directories=0)

        scanned_directories = 1
        child_candidates: list[CandidateNode] = []
        contains_content = False
        ignored_files: list[str] = []
        ignored_dirs: list[str] = []

        try:
            entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError:
            return _WalkNode(candidate=None, counts_as_content=True, scanned_directories=scanned_directories)

        for entry in entries:
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

                child = self._scan_dir(entry)
                scanned_directories += child.scanned_directories

                if child.candidate:
                    child_candidates.append(child.candidate)
                if child.counts_as_content:
                    contains_content = True
            else:
                file_relative = self._relative_path(entry)
                if self._matches_patterns(entry.name, file_relative, self.ignored_file_patterns):
                    ignored_files.append(entry.name)
                else:
                    contains_content = True

        if contains_content:
            return _WalkNode(candidate=None, counts_as_content=True, scanned_directories=scanned_directories)

        node = CandidateNode(
            path=path,
            relative_path=relative_path,
            ignored_files=sorted(set(ignored_files)),
            ignored_dirs=sorted(set(ignored_dirs)),
            children=child_candidates,
        )
        return _WalkNode(candidate=node, counts_as_content=False, scanned_directories=scanned_directories)

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
