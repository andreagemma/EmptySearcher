from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from send2trash import send2trash

from emptysearcher.config import AppConfig, load_config, save_config
from emptysearcher.scanner import CandidateNode, FolderScanner, ScanResult


PATH_ROLE = Qt.ItemDataRole.UserRole


class ScanWorker(QThread):
    scan_finished = Signal(object, str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = replace(config)

    def run(self) -> None:
        root = Path(self.config.root_folder).expanduser()
        scanner = FolderScanner(
            root=root,
            ignored_file_patterns=self.config.ignored_file_patterns,
            ignored_dir_patterns=self.config.ignored_dir_patterns,
            excluded_patterns=self.config.excluded_patterns,
        )
        result = scanner.scan()
        self.scan_finished.emit(result, str(root))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self._worker: ScanWorker | None = None
        self._current_root = Path(self.config.root_folder).expanduser() if self.config.root_folder else None

        self.setWindowTitle("EmptySearcher")
        self.resize(1400, 860)
        self._apply_palette()
        self._build_ui()
        self._load_config_into_widgets()
        self._restore_startup_state()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_rule_panel())
        splitter.addWidget(self._build_results_panel())
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Seleziona una cartella radice e avvia la scansione.")

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("HeaderCard")
        layout = QGridLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        title = QLabel("Rileva cartelle vuote o effettivamente vuote")
        title.setObjectName("HeroTitle")
        subtitle = QLabel(
            "I file ignorati e le cartelle ignorate non contano come contenuto. "
            "Gli elementi esclusi non vengono analizzati e non sono candidati all'eliminazione."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("HeroSubtitle")

        self.root_edit = QLineEdit()
        self.root_edit.setPlaceholderText("Cartella radice da analizzare")
        self.root_edit.editingFinished.connect(self._handle_root_edit_committed)

        browse_button = QPushButton("Sfoglia")
        browse_button.clicked.connect(self._choose_root)

        self.scan_button = QPushButton("Avvia scansione")
        self.scan_button.setObjectName("PrimaryButton")
        self.scan_button.clicked.connect(self._start_scan)

        self.save_config_button = QPushButton("Salva configurazione")
        self.save_config_button.clicked.connect(self._save_current_config)

        self.reload_config_button = QPushButton("Ricarica configurazione")
        self.reload_config_button.clicked.connect(self._reload_saved_config)

        self.delete_button = QPushButton("Elimina selezionate nel cestino")
        self.delete_button.clicked.connect(self._delete_checked_items)

        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(subtitle, 1, 0, 1, 4)
        layout.addWidget(self.root_edit, 2, 0, 1, 2)
        layout.addWidget(browse_button, 2, 2)
        layout.addWidget(self.scan_button, 2, 3)
        layout.addWidget(self.save_config_button, 3, 0)
        layout.addWidget(self.reload_config_button, 3, 1)
        layout.addWidget(self.delete_button, 3, 3)
        return frame

    def _build_rule_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("SideCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.ignored_files_list = QListWidget()
        self.ignored_dirs_list = QListWidget()
        self.excluded_list = QListWidget()
        for widget in (self.ignored_files_list, self.ignored_dirs_list, self.excluded_list):
            widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        layout.addWidget(self._build_pattern_group(
            "File ignorati",
            "Pattern come `Thumbs.db`, `*.tmp`, `*.log`.",
            self.ignored_files_list,
            self._add_ignored_file_pattern,
            lambda: self._remove_selected_pattern(self.ignored_files_list),
        ))
        layout.addWidget(self._build_pattern_group(
            "Cartelle ignorate",
            "Pattern di cartelle che non devono contare come contenuto.",
            self.ignored_dirs_list,
            self._add_ignored_dir_pattern,
            lambda: self._remove_selected_pattern(self.ignored_dirs_list),
        ))
        layout.addWidget(self._build_pattern_group(
            "Percorsi esclusi",
            "Pattern esclusi dalla ricerca e dai risultati.",
            self.excluded_list,
            self._add_excluded_pattern,
            lambda: self._remove_selected_pattern(self.excluded_list),
        ))
        layout.addStretch(1)
        return panel

    def _build_pattern_group(
        self,
        title: str,
        description: str,
        list_widget: QListWidget,
        add_handler,
        remove_handler,
    ) -> QWidget:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        layout.addWidget(list_widget, 1)

        actions = QHBoxLayout()
        add_button = QPushButton("Aggiungi")
        add_button.clicked.connect(add_handler)
        remove_button = QPushButton("Rimuovi")
        remove_button.clicked.connect(remove_handler)
        actions.addWidget(add_button)
        actions.addWidget(remove_button)
        layout.addLayout(actions)
        return box

    def _build_results_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("ResultsCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.summary_label = QLabel("Nessuna scansione eseguita.")
        self.summary_label.setObjectName("SummaryLabel")

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Cartella", "Percorso relativo", "File ignorati", "Cartelle ignorate"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_tree_menu)
        self.tree.itemChanged.connect(self._propagate_check_state)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Dettagli della scansione e suggerimenti operativi.")
        self.details.setMaximumHeight(150)

        layout.addWidget(self.summary_label)
        layout.addWidget(self.tree, 1)
        layout.addWidget(self.details)
        return panel

    def _apply_palette(self) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f2f5f9"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#17202b"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#eef3f8"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#17202b"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#17202b"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#17202b"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#0c7d69"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        QApplication.instance().setPalette(palette)
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Segoe UI", "SF Pro Text", "Noto Sans", sans-serif;
                font-size: 13px;
            }
            QFrame#HeaderCard, QFrame#SideCard, QFrame#ResultsCard, QGroupBox {
                background: #ffffff;
                border: 1px solid #d7e0ea;
                border-radius: 18px;
            }
            QGroupBox {
                padding-top: 14px;
                margin-top: 6px;
                font-weight: 600;
            }
            QLabel#HeroTitle {
                font-size: 24px;
                font-weight: 700;
                color: #102030;
            }
            QLabel#HeroSubtitle, QTextEdit, QListWidget {
                color: #405261;
            }
            QLabel#SummaryLabel {
                font-size: 15px;
                font-weight: 600;
                color: #102030;
            }
            QPushButton {
                min-height: 36px;
                border-radius: 12px;
                border: 1px solid #cfd8e3;
                padding: 0 14px;
                background: #ffffff;
            }
            QPushButton#PrimaryButton {
                background: #0c7d69;
                color: #ffffff;
                border: none;
                font-weight: 700;
            }
            QLineEdit, QListWidget, QTextEdit, QTreeWidget {
                border: 1px solid #d1dbe6;
                border-radius: 14px;
                padding: 8px;
                background: #ffffff;
            }
            QHeaderView::section {
                background: #edf3f8;
                border: none;
                border-bottom: 1px solid #d1dbe6;
                padding: 8px;
                font-weight: 600;
            }
            """
        )

    def _load_config_into_widgets(self) -> None:
        self.root_edit.setText(self.config.root_folder)
        self._refresh_pattern_list(self.ignored_files_list, self.config.ignored_file_patterns)
        self._refresh_pattern_list(self.ignored_dirs_list, self.config.ignored_dir_patterns)
        self._refresh_pattern_list(self.excluded_list, self.config.excluded_patterns)

    def _restore_startup_state(self) -> None:
        restored_root = self.config.root_folder.strip()
        last_selected = self.config.last_selected_folder.strip()
        if restored_root:
            self.statusBar().showMessage(f"Configurazione ripristinata. Cartella corrente: {restored_root}")
        elif last_selected:
            self.statusBar().showMessage(f"Configurazione ripristinata. Ultima cartella selezionata: {last_selected}")

    def _refresh_pattern_list(self, widget: QListWidget, values: list[str]) -> None:
        widget.clear()
        for value in values:
            widget.addItem(QListWidgetItem(value))

    def _choose_root(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Seleziona cartella radice",
            self._folder_dialog_start_path(),
        )
        if selected:
            self.root_edit.setText(selected)
            self._commit_root_folder(selected, persist=True)

    def _start_scan(self) -> None:
        root_text = self.root_edit.text().strip()
        if not root_text:
            QMessageBox.warning(self, "Cartella mancante", "Seleziona una cartella radice prima di avviare la scansione.")
            return

        root = Path(root_text).expanduser()
        if not root.exists() or not root.is_dir():
            QMessageBox.warning(self, "Percorso non valido", "La cartella radice selezionata non esiste o non e' accessibile.")
            return

        self._update_config_from_widgets()
        self._persist_config()
        self._current_root = root

        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.tree.clear()
        self.summary_label.setText("Scansione in corso...")
        self.details.setPlainText("Analisi della struttura cartelle in corso.")
        self.statusBar().showMessage(f"Scansione di {root}")

        self._worker = ScanWorker(self.config)
        self._worker.scan_finished.connect(self._handle_scan_finished)
        self._worker.start()

    def _handle_scan_finished(self, result: ScanResult, root_text: str) -> None:
        self.scan_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self._worker = None

        self.tree.blockSignals(True)
        self.tree.clear()
        for node in result.roots:
            self.tree.addTopLevelItem(self._build_tree_item(node))
        self.tree.expandToDepth(1)
        self.tree.blockSignals(False)

        total = self._count_items()
        self.summary_label.setText(f"Trovate {total} cartelle candidate in {result.scanned_directories} cartelle analizzate.")
        self.details.setPlainText(
            "Le cartelle selezionate verranno inviate al cestino di sistema. "
            "Le cartelle candidate possono contenere file o sottocartelle ignorate."
        )
        self.statusBar().showMessage(f"Scansione completata su {root_text}")

    def _build_tree_item(self, node: CandidateNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem(
            [
                node.path.name or str(node.path),
                node.relative_path,
                ", ".join(node.ignored_files) or "-",
                ", ".join(node.ignored_dirs) or "-",
            ]
        )
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setData(0, PATH_ROLE, str(node.path))

        for child in node.children:
            item.addChild(self._build_tree_item(child))
        return item

    def _propagate_check_state(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        state = item.checkState(0)
        for index in range(item.childCount()):
            child = item.child(index)
            child.setCheckState(0, state)

    def _show_tree_menu(self, position) -> None:
        item = self.tree.itemAt(position)
        if item is None:
            return

        path_text = item.data(0, PATH_ROLE)
        if not path_text:
            return

        path = Path(path_text)
        relative = self._relative_to_root(path)

        menu = QMenu(self)
        ignore_action = QAction("Aggiungi ai pattern cartelle ignorate", self)
        ignore_action.triggered.connect(lambda: self._append_pattern(self.ignored_dirs_list, relative, rescan=True))

        exclude_action = QAction("Aggiungi ai pattern esclusi", self)
        exclude_action.triggered.connect(lambda: self._append_pattern(self.excluded_list, relative, rescan=True))

        delete_action = QAction("Invia questa cartella al cestino", self)
        delete_action.triggered.connect(lambda: self._trash_paths([path]))

        menu.addAction(ignore_action)
        menu.addAction(exclude_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _add_ignored_file_pattern(self) -> None:
        self._prompt_and_add_pattern(self.ignored_files_list, "Nuovo pattern file", "Inserisci un pattern file da ignorare:")

    def _add_ignored_dir_pattern(self) -> None:
        self._prompt_and_add_pattern(self.ignored_dirs_list, "Nuovo pattern cartella", "Inserisci un pattern cartella da ignorare:")

    def _add_excluded_pattern(self) -> None:
        self._prompt_and_add_pattern(self.excluded_list, "Nuovo pattern escluso", "Inserisci un pattern da escludere dalla ricerca:")

    def _prompt_and_add_pattern(self, widget: QListWidget, title: str, label: str) -> None:
        value, accepted = QInputDialog.getText(self, title, label)
        if accepted:
            self._append_pattern(widget, value)

    def _append_pattern(self, widget: QListWidget, value: str, rescan: bool = False) -> None:
        cleaned = value.strip()
        if not cleaned:
            return
        existing = {widget.item(index).text() for index in range(widget.count())}
        if cleaned not in existing:
            widget.addItem(QListWidgetItem(cleaned))
            self._update_config_from_widgets()
            self._persist_config()
            if rescan:
                self._start_scan()

    def _remove_selected_pattern(self, widget: QListWidget) -> None:
        row = widget.currentRow()
        if row >= 0:
            widget.takeItem(row)
            self._update_config_from_widgets()
            self._persist_config()

    def _update_config_from_widgets(self) -> None:
        self._commit_root_folder(self.root_edit.text().strip(), persist=False)
        self.config.ignored_file_patterns = self._patterns_from_widget(self.ignored_files_list)
        self.config.ignored_dir_patterns = self._patterns_from_widget(self.ignored_dirs_list)
        self.config.excluded_patterns = self._patterns_from_widget(self.excluded_list)

    def _persist_config(self) -> None:
        save_config(self.config)

    def _save_current_config(self) -> None:
        self._update_config_from_widgets()
        self._persist_config()
        self.statusBar().showMessage("Configurazione salvata.")

    def _reload_saved_config(self) -> None:
        self.config = load_config()
        self._current_root = Path(self.config.root_folder).expanduser() if self.config.root_folder else None
        self._load_config_into_widgets()
        self.tree.clear()
        self.summary_label.setText("Configurazione ricaricata. Avvia una nuova scansione.")
        self.details.clear()
        self._restore_startup_state()

    def _handle_root_edit_committed(self) -> None:
        self._commit_root_folder(self.root_edit.text().strip(), persist=True)

    def _commit_root_folder(self, root_text: str, persist: bool) -> None:
        normalized = str(Path(root_text).expanduser()) if root_text else ""
        self.config.root_folder = normalized

        if normalized:
            candidate = Path(normalized)
            if candidate.exists() and candidate.is_dir():
                resolved = str(candidate)
                self.config.root_folder = resolved
                self.config.last_selected_folder = resolved
                self._current_root = candidate
        if persist:
            self._persist_config()

    @staticmethod
    def _patterns_from_widget(widget: QListWidget) -> list[str]:
        return [widget.item(index).text() for index in range(widget.count())]

    def _delete_checked_items(self) -> None:
        paths = self._checked_paths()
        if not paths:
            QMessageBox.information(self, "Nessuna selezione", "Non ci sono cartelle selezionate da eliminare.")
            return

        names = "\n".join(str(path) for path in paths[:10])
        extra = "" if len(paths) <= 10 else f"\n... e altre {len(paths) - 10} cartelle"
        answer = QMessageBox.question(
            self,
            "Conferma eliminazione",
            f"Le cartelle selezionate saranno inviate al cestino:\n\n{names}{extra}",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._trash_paths(paths)

    def _trash_paths(self, paths: list[Path]) -> None:
        unique_paths = self._collapse_descendants(paths)
        failures: list[str] = []
        deleted = 0
        for path in unique_paths:
            try:
                if path.exists():
                    send2trash(str(path))
                    deleted += 1
            except Exception as exc:  # pragma: no cover - GUI path
                failures.append(f"{path}: {exc}")

        if failures:
            QMessageBox.warning(self, "Eliminazione parziale", "\n".join(failures))
        else:
            QMessageBox.information(self, "Eliminazione completata", f"Inviate al cestino {deleted} cartelle.")

        self._start_scan()

    def _checked_paths(self) -> list[Path]:
        collected: list[Path] = []

        def visit(item: QTreeWidgetItem) -> None:
            if item.checkState(0) == Qt.CheckState.Checked:
                path_text = item.data(0, PATH_ROLE)
                if path_text:
                    collected.append(Path(path_text))
            for index in range(item.childCount()):
                visit(item.child(index))

        for index in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(index))
        return collected

    def _count_items(self) -> int:
        total = 0

        def visit(item: QTreeWidgetItem) -> None:
            nonlocal total
            total += 1
            for child_index in range(item.childCount()):
                visit(item.child(child_index))

        for index in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(index))
        return total

    @staticmethod
    def _collapse_descendants(paths: list[Path]) -> list[Path]:
        ordered = sorted({path.resolve() for path in paths}, key=lambda path: len(path.parts))
        selected: list[Path] = []
        for path in ordered:
            if not any(parent in path.parents for parent in selected):
                selected.append(path)
        return selected

    def _relative_to_root(self, path: Path) -> str:
        if self._current_root is None:
            return path.name
        try:
            rel = path.relative_to(self._current_root)
        except ValueError:
            return path.name
        return rel.as_posix() or "."

    def _folder_dialog_start_path(self) -> str:
        current = self.root_edit.text().strip()
        for candidate_text in (current, self.config.last_selected_folder):
            if not candidate_text:
                continue
            candidate = Path(candidate_text).expanduser()
            if candidate.exists() and candidate.is_dir():
                return str(candidate)
            if candidate.parent.exists():
                return str(candidate.parent)
        return str(Path.home())

    def closeEvent(self, event: QCloseEvent) -> None:
        self._update_config_from_widgets()
        self._persist_config()
        super().closeEvent(event)
