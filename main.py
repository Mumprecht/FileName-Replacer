from __future__ import annotations

import json
import os
import re
import tkinter as tk
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_TITLE = 'FileName-Replacer'
APP_VERSION = '0.2.1'
COPYRIGHT = '© 2026 Urs Mumprecht'
REPOSITORY_URL = 'https://github.com/Mumprecht/FileName-Replacer'


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base / relative

TEST_FOLDER = 'Testdaten'
MARKER = '.filename_replacer_test.json'
INVALID = set('<>:"/\\|?*')
RESERVED = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$', re.I)
TEST_FILES = (
    'Mein Dokument 01.txt', 'Foto Sommer 2026.jpg',
    'Unterordner A/Test Datei 02.txt', 'Unterordner A/Weitere Datei.pdf',
    'Unterordner B/Noch ein Test.txt',
    'Unterordner B/Tiefer Ordner/Letzte Datei.txt',
)
TEST_CONTENT = 'Testdatei für FileName-Replacer\n'


@dataclass(frozen=True)
class Change:
    source: Path
    target: Path
    kind: str
    error: str = ''


def valid_name(name: str) -> bool:
    return (bool(name) and name not in ('.', '..')
            and not any(ch in INVALID or ord(ch) < 32 for ch in name)
            and not name.endswith((' ', '.'))
            and not RESERVED.fullmatch(name))


def key(path: Path) -> str:
    return os.path.normcase(str(path)).casefold()


def collect_changes(folder: Path, old: str, new: str, recursive: bool,
                    files_enabled: bool, folders_enabled: bool) -> list[Change]:
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError('Bitte ein vorhandenes, reguläres Verzeichnis auswählen.')
    if len(old) != 1 or len(new) != 1 or not valid_name('A' + old + 'A') or not valid_name('A' + new + 'A'):
        raise ValueError('Such- und Ersatzzeichen müssen jeweils genau ein gültiges Zeichen sein.')
    if not (files_enabled or folders_enabled):
        raise ValueError('Bitte Dateien und/oder Ordner auswählen.')

    paths = list(folder.rglob('*') if recursive else folder.iterdir())
    changes: list[Change] = []
    for path in paths:
        if path.is_symlink():
            continue
        is_file = path.is_file()
        is_dir = path.is_dir()
        if not ((is_file and files_enabled) or (is_dir and folders_enabled)):
            continue
        if path.name == MARKER or old not in path.name:
            continue
        target = path.with_name(path.name.replace(old, new))
        if target == path:
            continue
        kind = 'Ordner' if is_dir else 'Datei'
        error = '' if valid_name(target.name) else 'Ungültiger Zielname'
        changes.append(Change(path, target, kind, error))

    # Änderungen erfolgen immer von unten nach oben. Dadurch bleiben Quellpfade
    # tiefer liegender Dateien/Ordner gültig, bis sie verarbeitet wurden.
    changes.sort(key=lambda c: (-len(c.source.parts), c.kind != 'Datei', key(c.source)))
    by_parent: dict[str, list[Change]] = {}
    for change in changes:
        by_parent.setdefault(key(change.source.parent), []).append(change)

    errors: dict[Path, str] = {}
    for siblings in by_parent.values():
        destinations: dict[str, list[Change]] = {}
        for change in siblings:
            destinations.setdefault(key(change.target), []).append(change)
        for change in siblings:
            if change.error:
                errors[change.source] = change.error
            elif len(destinations[key(change.target)]) > 1:
                errors[change.source] = 'Mehrere Elemente mit gleichem Zielnamen'
            elif change.target.exists() or change.target.is_symlink():
                errors[change.source] = 'Ziel bereits vorhanden'
            else:
                # Auf Windows können sich Namen nur in Gross-/Kleinschreibung unterscheiden.
                try:
                    if any(key(other) == key(change.target) for other in change.source.parent.iterdir()
                           if other != change.source):
                        errors[change.source] = 'Zielname bereits vorhanden'
                except OSError as exc:
                    errors[change.source] = str(exc)
    return [Change(c.source, c.target, c.kind, errors.get(c.source, '')) for c in changes]


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f'{APP_TITLE} v{APP_VERSION}')
        self._apply_icon()
        self.geometry('1120x720')
        self.minsize(830, 540)
        self.folder = tk.StringVar(value=str(Path.cwd()))
        self.search = tk.StringVar(value=' ')
        self.replace = tk.StringVar(value='_')
        self.recursive = tk.BooleanVar(value=False)
        self.files_enabled = tk.BooleanVar(value=True)
        self.folders_enabled = tk.BooleanVar(value=False)
        self.changes: list[Change] = []
        self.undo: list[tuple[Path, Path, str]] = []
        self._build()

    def _apply_icon(self) -> None:
        icon = resource_path('resources/FileName-Replacer.ico')
        if icon.is_file():
            try:
                self.iconbitmap(default=str(icon))
            except tk.TclError:
                pass

    def show_about(self) -> None:
        window = tk.Toplevel(self)
        window.title(f'Über {APP_TITLE}')
        window.geometry('560x410')
        window.resizable(False, False)
        window.transient(self)
        window.grab_set()
        icon = resource_path('resources/FileName-Replacer.ico')
        if icon.is_file():
            try:
                window.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
        frame = ttk.Frame(window, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=APP_TITLE, font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text=f'Version {APP_VERSION}', font=('Segoe UI', 11)).pack(anchor='w', pady=(5, 0))
        ttk.Label(frame, text=COPYRIGHT).pack(anchor='w', pady=(8, 16))
        ttk.Label(frame, text='Dateien und Ordner sicher und kontrolliert umbenennen.\n'
                              'Mit Vorschau, Unterordnerverarbeitung und Rückgängig-Funktion.',
                  justify='left').pack(anchor='w')
        ttk.Separator(frame).pack(fill='x', pady=16)
        ttk.Label(frame, text='Lizenz: MIT License', font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Kostenlose Nutzung, Änderung und Weitergabe sind erlaubt,\n'
                              'auch kommerziell. Copyright- und Lizenzhinweis müssen\n'
                              'bei Weitergabe erhalten bleiben.', justify='left').pack(anchor='w', pady=(5, 12))
        link = ttk.Label(frame, text='GitHub-Projekt öffnen', foreground='#0066cc', cursor='hand2')
        link.pack(anchor='w')
        link.bind('<Button-1>', lambda _event: webbrowser.open(REPOSITORY_URL))
        buttons = ttk.Frame(frame)
        buttons.pack(side='bottom', fill='x', pady=(18, 0))
        ttk.Button(buttons, text='Lizenztext anzeigen', command=self.show_license).pack(side='left')
        ttk.Button(buttons, text='Schliessen', command=window.destroy).pack(side='right')
        window.bind('<Escape>', lambda _event: window.destroy())
        window.wait_window()

    def show_license(self) -> None:
        license_path = resource_path('LICENSE')
        try:
            license_text = license_path.read_text(encoding='utf-8')
        except OSError:
            messagebox.showerror(APP_TITLE, 'Die Lizenzdatei wurde nicht gefunden.')
            return
        dialog = tk.Toplevel(self)
        dialog.title('MIT-Lizenz')
        dialog.geometry('720x500')
        dialog.transient(self)
        content = ttk.Frame(dialog, padding=12)
        content.pack(fill='both', expand=True)
        text = tk.Text(content, wrap='word', padx=10, pady=10)
        text.insert('1.0', license_text)
        text.configure(state='disabled')
        text.pack(fill='both', expand=True)
        ttk.Button(content, text='Schliessen', command=dialog.destroy).pack(anchor='e', pady=(8, 0))

    def _build(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label='Beenden', command=self.destroy)
        menubar.add_cascade(label='Datei', menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label='Über FileName-Replacer', command=self.show_about)
        help_menu.add_command(label='MIT-Lizenz anzeigen', command=self.show_license)
        menubar.add_cascade(label='Hilfe', menu=help_menu)
        self.config(menu=menubar)
        panel = ttk.Frame(self, padding=14)
        panel.pack(fill='both', expand=True)
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text='Verzeichnis:').grid(row=0, column=0, sticky='w')
        ttk.Entry(panel, textvariable=self.folder).grid(row=0, column=1, sticky='ew', padx=8)
        ttk.Button(panel, text='Durchsuchen', command=self.browse).grid(row=0, column=2)

        options = ttk.Frame(panel)
        options.grid(row=1, column=0, columnspan=3, sticky='w', pady=(15, 6))
        ttk.Label(options, text='Suchen:').pack(side='left')
        ttk.Entry(options, textvariable=self.search, width=12).pack(side='left', padx=(6, 20))
        ttk.Label(options, text='Ersetzen durch:').pack(side='left')
        ttk.Entry(options, textvariable=self.replace, width=12).pack(side='left', padx=6)

        kinds = ttk.Frame(panel)
        kinds.grid(row=2, column=0, columnspan=3, sticky='w', pady=4)
        ttk.Checkbutton(kinds, text='Dateien umbenennen', variable=self.files_enabled).pack(side='left', padx=(0, 22))
        ttk.Checkbutton(kinds, text='Ordner umbenennen', variable=self.folders_enabled).pack(side='left')
        ttk.Checkbutton(panel, text='Unterordner ebenfalls berücksichtigen',
                        variable=self.recursive).grid(row=3, column=0, columnspan=3, sticky='w', pady=5)

        actions = ttk.Frame(panel)
        actions.grid(row=4, column=0, columnspan=3, sticky='w', pady=(6, 12))
        for label, action in (
            ('Vorschau aktualisieren', self.preview),
            ('Ausgewählte Elemente umbenennen', self.rename),
            ('Letzte Aktion rückgängig', self.undo_last),
            ('Testordner erstellen', self.create_test),
            ('Testordner löschen', self.delete_test),
            ('Beenden', self.destroy),
        ):
            ttk.Button(actions, text=label, command=action).pack(side='left', padx=(0, 7), pady=3)

        ttk.Label(panel, text='Vorschau / Ergebnis:').grid(row=5, column=0, columnspan=3, sticky='w')
        frame = ttk.Frame(panel)
        frame.grid(row=6, column=0, columnspan=3, sticky='nsew', pady=(6, 8))
        panel.rowconfigure(6, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(frame, columns=('kind', 'source', 'target', 'status'), show='headings')
        for name, title, width in (
            ('kind', 'Typ', 75), ('source', 'Bisheriger Pfad', 390),
            ('target', 'Neuer Pfad', 390), ('status', 'Status', 180),
        ):
            self.table.heading(name, text=title)
            self.table.column(name, width=width, stretch=name != 'kind')
        self.table.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(frame, orient='vertical', command=self.table.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=scroll.set)
        self.status = tk.StringVar(value='Bereit. Zuerst Vorschau erstellen.')
        ttk.Label(panel, textvariable=self.status).grid(row=7, column=0, columnspan=2, sticky='w')
        ttk.Label(panel, text=f'v{APP_VERSION}  |  {COPYRIGHT}').grid(row=7, column=2, sticky='e')
        for var in (self.folder, self.search, self.replace, self.recursive,
                    self.files_enabled, self.folders_enabled):
            var.trace_add('write', self.invalidate)

    def invalidate(self, *_: object) -> None:
        self.changes.clear()
        self.table.delete(*self.table.get_children())
        self.status.set('Einstellungen geändert – Vorschau erneut erstellen.')

    def browse(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.folder.get())
        if folder:
            self.folder.set(folder)

    def selected_folder(self) -> Path | None:
        folder = Path(self.folder.get().strip())
        if not folder.is_dir() or folder.is_symlink():
            messagebox.showerror(APP_TITLE, 'Bitte ein vorhandenes Verzeichnis auswählen (keine Verknüpfung).')
            return None
        return folder.resolve()

    def get_changes(self, folder: Path) -> list[Change]:
        return collect_changes(folder, self.search.get(), self.replace.get(),
                               self.recursive.get(), self.files_enabled.get(),
                               self.folders_enabled.get())

    def preview(self) -> None:
        folder = self.selected_folder()
        if folder is None:
            return
        try:
            changes = self.get_changes(folder)
        except (OSError, ValueError) as exc:
            self.invalidate()
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.changes = changes
        self.table.delete(*self.table.get_children())
        for c in changes:
            self.table.insert('', 'end', values=(c.kind, str(c.source.relative_to(folder)),
                                                 str(c.target.relative_to(folder)), c.error or 'Bereit'))
        self.status.set(f'{len(changes)} Änderungen gefunden; {sum(bool(c.error) for c in changes)} Konflikte.')

    def rename(self) -> None:
        if not self.changes:
            messagebox.showinfo(APP_TITLE, 'Bitte zuerst eine Vorschau mit Änderungen erstellen.')
            return
        if any(c.error for c in self.changes):
            messagebox.showerror(APP_TITLE, 'Konflikte vorhanden. Es wird nichts umbenannt.')
            return
        folder = self.selected_folder()
        if folder is None:
            return
        try:
            fresh = self.get_changes(folder)
        except (OSError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        if fresh != self.changes or any(c.error for c in fresh):
            self.invalidate()
            messagebox.showerror(APP_TITLE, 'Dateisystem geändert. Bitte Vorschau aktualisieren.')
            return
        if not messagebox.askyesno(APP_TITLE, f'{len(fresh)} Dateien/Ordner wirklich umbenennen?'):
            return
        completed: list[tuple[Path, Path, str]] = []
        try:
            for c in fresh:
                if not c.source.exists() or c.target.exists() or c.target.is_symlink():
                    raise OSError(f'Quelle fehlt oder Ziel existiert: {c.source}')
                c.source.rename(c.target)
                completed.append((c.source, c.target, c.kind))
        except OSError as exc:
            self.undo = completed
            messagebox.showerror(APP_TITLE, f'Abgebrochen: {exc}\nBereits umbenannt: {len(completed)}.\n'
                                            'Diese können mit Rückgängig zurückgesetzt werden.')
        else:
            self.undo = completed
            messagebox.showinfo(APP_TITLE, f'{len(completed)} Elemente erfolgreich umbenannt.')
        self.invalidate()

    def undo_last(self) -> None:
        if not self.undo:
            messagebox.showinfo(APP_TITLE, 'Keine Umbenennung zum Rückgängigmachen vorhanden.')
            return
        if not messagebox.askyesno(APP_TITLE, f'{len(self.undo)} Umbenennungen rückgängig machen?'):
            return
        remaining: list[tuple[Path, Path, str]] = []
        # Rückwärts: zuerst übergeordnete Ordner zurückbenennen, dann deren Inhalte.
        for original, renamed, kind in reversed(self.undo):
            try:
                exists = renamed.is_dir() if kind == 'Ordner' else renamed.is_file()
                if not exists or original.exists() or original.is_symlink():
                    remaining.append((original, renamed, kind))
                    continue
                renamed.rename(original)
            except OSError:
                remaining.append((original, renamed, kind))
        self.undo = list(reversed(remaining))
        self.invalidate()
        messagebox.showinfo(APP_TITLE, f'Rückgängig abgeschlossen. Nicht zurückgesetzt: {len(remaining)}')

    def test_path(self) -> Path | None:
        folder = self.selected_folder()
        return folder / TEST_FOLDER if folder else None

    def create_test(self) -> None:
        target = self.test_path()
        if target is None:
            return
        if target.exists() or target.is_symlink():
            messagebox.showerror(APP_TITLE, 'Testdaten existiert bereits. Es wird nichts überschrieben.')
            return
        try:
            target.mkdir()
            for relative in TEST_FILES:
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(TEST_CONTENT, encoding='utf-8')
            (target / MARKER).write_text(json.dumps({'app': APP_TITLE, 'version': 2}), encoding='utf-8')
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f'Testdaten nicht vollständig erstellt: {exc}')
            return
        self.folder.set(str(target))
        messagebox.showinfo(APP_TITLE, f'Testdaten erstellt:\n{target}')

    def delete_test(self) -> None:
        selected = self.selected_folder()
        if selected is None:
            return
        target = selected if selected.name == TEST_FOLDER else selected / TEST_FOLDER
        marker = target / MARKER
        try:
            if not target.is_dir() or target.is_symlink() or not marker.is_file() or marker.is_symlink():
                raise ValueError('Kein eindeutig markierter Testordner gefunden.')
            data = json.loads(marker.read_text(encoding='utf-8'))
            if data not in ({'app': APP_TITLE, 'version': 1}, {'app': APP_TITLE, 'version': 2}):
                raise ValueError('Ungültige Testordner-Kennung.')
            paths = list(target.rglob('*'))
            if any(p.is_symlink() for p in paths):
                raise ValueError('Verknüpfung im Testordner gefunden. Löschen verweigert.')
            actual_files = [p for p in paths if p.is_file() and p != marker]
            if len(actual_files) != len(TEST_FILES) or any(
                p.read_text(encoding='utf-8') != TEST_CONTENT for p in actual_files
            ):
                raise ValueError('Testordner enthält unbekannte oder veränderte Dateien. Löschen verweigert.')
            expected_dirs = {Path(x).parent for x in TEST_FILES if len(Path(x).parts) > 1}
            expected_count = len({str(p) for d in expected_dirs for p in (d, *d.parents) if str(p) != '.'})
            actual_dirs = [p for p in paths if p.is_dir()]
            if len(actual_dirs) != expected_count or len(paths) != len(actual_files) + len(actual_dirs) + 1:
                raise ValueError('Testordnerstruktur wurde verändert. Löschen verweigert.')
            if not messagebox.askyesno(APP_TITLE, f'Testordner samt Inhalt unwiderruflich löschen?\n{target}'):
                return
            for p in sorted(paths, key=lambda x: len(x.parts), reverse=True):
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    p.rmdir()
            target.rmdir()
            self.undo.clear()
            self.folder.set(str(target.parent))
            messagebox.showinfo(APP_TITLE, 'Testordner gelöscht.')
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))


if __name__ == '__main__':
    Application().mainloop()
