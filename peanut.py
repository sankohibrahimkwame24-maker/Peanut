# ============================================================
# PEANUT - FINAL V2 PRODUCTION SOURCE
# ============================================================
# Purpose:
# This is the final Peanut V2 application source code.
#
# Peanut takes a folder selected by the user and organizes the
# files directly inside that folder into clear categories.
#
# V1 proved the core idea as a Python script.
# V2 turns that idea into a production-style desktop application
# with a GUI, safety checks, duplicate protection, error handling,
# background processing, logging, and packaging support.
# ============================================================

import os
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path as FilePath

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


# ============================================================
# APPLICATION INFORMATION
# ============================================================
# Keep the name and version in one place so the UI, logs, and
# packaged application all refer to the same product identity.
# ============================================================

APP_NAME = "Peanut"
APP_VERSION = "2.0.0"


# ============================================================
# VISUAL DESIGN
# ============================================================
# This stylesheet keeps the interface consistent without requiring
# an external UI file. Layouts remain responsible for positioning,
# so the interface can adapt to different window sizes.
# ============================================================

APP_STYLE = """
QMainWindow, QWidget {
    background: #0B0F17;
    color: #F8FAFC;
    font-family: "Segoe UI";
}

QLabel#title {
    font-size: 32px;
    font-weight: 700;
}

QLabel#subtitle, QLabel#muted {
    color: #94A3B8;
    font-size: 15px;
}

QLabel#status {
    color: #CBD5E1;
    font-size: 14px;
}

QFrame#card {
    background: #111827;
    border: 1px solid #243044;
    border-radius: 18px;
}

QPushButton {
    background: #3B82F6;
    color: white;
    border: none;
    border-radius: 12px;
    padding: 13px 22px;
    font-size: 15px;
    font-weight: 600;
}

QPushButton:hover {
    background: #2563EB;
}

QPushButton:disabled {
    background: #334155;
    color: #94A3B8;
}

QPushButton#secondary {
    background: #172033;
    border: 1px solid #334155;
}

QPushButton#secondary:hover {
    background: #1E293B;
}

QProgressBar {
    background: #172033;
    border: none;
    border-radius: 8px;
    height: 14px;
    text-align: center;
}

QProgressBar::chunk {
    background: #3B82F6;
    border-radius: 8px;
}
"""


# ============================================================
# FILE CATEGORIES
# ============================================================
# Each category contains the file extensions Peanut recognizes.
# Anything not listed is intentionally sent to "Others" instead
# of being deleted, ignored, or guessed incorrectly.
# ============================================================

CATEGORIES = {
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"
    },
    "Videos": {
        ".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv"
    },
    "Audio": {
        ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"
    },
    "Documents": {
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
        ".xls", ".xlsx", ".csv", ".ppt", ".pptx"
    },
    "Archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"
    },
    "Code": {
        ".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
        ".java", ".cpp", ".c", ".h", ".cs", ".php", ".sql"
    },
    "CAD": {
        ".f3d", ".stl", ".step", ".stp", ".iges", ".igs", ".dwg", ".dxf"
    },
}


# ============================================================
# SAFETY CONFIGURATION
# ============================================================
# Peanut must never reorganize Windows system/application locations.
# We build the blacklist dynamically from Windows environment
# variables instead of hardcoding one user's drive letter/path.
# ============================================================

PROTECTED_ENVIRONMENT_PATHS = (
    "SystemRoot",
    "ProgramFiles",
    "ProgramFiles(x86)",
    "ProgramData",
    "CommonProgramFiles",
    "CommonProgramFiles(x86)",
    "CommonProgramW6432",
)


# ============================================================
# FILE CLASSIFICATION
# ============================================================
# Convert a file extension into one of Peanut's categories.
# Unknown extensions are deliberately kept safe by using "Others".
# ============================================================

def category_for(extension):
    extension = extension.lower()

    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category

    return "Others"


# ============================================================
# PATH SAFETY
# ============================================================
# Return the Windows directories that Peanut must protect.
# pathlib is used so paths are handled safely across Windows path
# formatting instead of relying on manually typed strings.
# ============================================================

def forbidden_paths():
    protected = []

    for environment_name in PROTECTED_ENVIRONMENT_PATHS:
        value = os.environ.get(environment_name)

        if value:
            path = FilePath(value).resolve()

            if path.exists() and path not in protected:
                protected.append(path)

    return protected


# ============================================================
# SOURCE-FOLDER SAFETY CHECK
# ============================================================
# A user might accidentally choose C:\, Windows, Program Files,
# or another protected location. Peanut blocks these before any
# file operation can happen.
#
# We also resolve the selected path first. That matters because a
# shortcut, symbolic link, or junction can otherwise hide where the
# path actually points.
# ============================================================

def is_forbidden_source(path):
    resolved = FilePath(path).resolve()

    # Never allow a drive root such as C:\ or D:\.
    if resolved.parent == resolved:
        return True

    for protected in forbidden_paths():
        if resolved == protected:
            return True

        # Also block any folder living inside a protected directory.
        try:
            resolved.relative_to(protected)
            return True
        except ValueError:
            pass

    return False


# ============================================================
# DESTINATION SAFETY
# ============================================================
# Category folders are created inside the selected source folder.
# This helper checks that the final directory has not escaped the
# selected folder through a symbolic link or other path trick.
# ============================================================

def safe_category_folder(source, category):
    source_resolved = FilePath(source).resolve()
    destination_folder = source_resolved / category

    # Refuse to follow a symbolic link that already exists as a
    # category folder. Peanut should create real folders itself.
    if destination_folder.exists() and destination_folder.is_symlink():
        raise PermissionError(
            f"The {category} folder is a symbolic link. Peanut will not use it."
        )

    destination_folder.mkdir(exist_ok=True)
    destination_resolved = destination_folder.resolve()

    try:
        destination_resolved.relative_to(source_resolved)
    except ValueError as error:
        raise PermissionError(
            f"The {category} destination is outside the selected folder."
        ) from error

    return destination_resolved


# ============================================================
# DUPLICATE-FILE PROTECTION
# ============================================================
# Peanut must never overwrite an existing file.
#
# Example:
# report.pdf
# report (1).pdf
# report (2).pdf
# ============================================================

def unique_destination(path):
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1

    while True:
        candidate = path.with_name(f"{stem} ({counter}){suffix}")

        if not candidate.exists():
            return candidate

        counter += 1


# ============================================================
# APPLICATION LOGGING
# ============================================================
# Production applications need a place to record technical problems
# without exposing a huge traceback to a normal user.
# ============================================================

def application_log_directory():
    if os.name == "nt":
        base = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or str(FilePath.home() / "AppData" / "Local")
        )
    else:
        base = os.environ.get(
            "XDG_STATE_HOME",
            str(FilePath.home() / ".local" / "state"),
        )

    log_directory = FilePath(base) / APP_NAME / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    return log_directory


def write_log(title, details):
    """Write a human-readable technical log and return its file path."""
    try:
        log_file = application_log_directory() / "peanut.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with log_file.open("a", encoding="utf-8") as file:
            file.write("\n" + "=" * 72 + "\n")
            file.write(f"{timestamp} | {APP_NAME} {APP_VERSION}\n")
            file.write(f"{title}\n")
            file.write("-" * 72 + "\n")
            file.write(str(details).rstrip() + "\n")

        return log_file
    except OSError:
        # Logging must never be allowed to crash the organizer.
        return None


# ============================================================
# FILE-ORGANIZATION ENGINE
# ============================================================
# This is the core business logic, intentionally separated from
# the graphical interface.
#
# That separation makes Peanut easier to understand, test, maintain,
# and package because the engine does not depend on button clicks.
# ============================================================

def organize_folder(source, progress_callback=None, status_callback=None):
    source = FilePath(source).resolve()

    # Validate the selected source before touching any file.
    if not source.exists():
        raise FileNotFoundError("The selected folder no longer exists.")

    if not source.is_dir():
        raise NotADirectoryError("The selected location is not a folder.")

    if is_forbidden_source(source):
        raise PermissionError(
            "Peanut will not organize protected Windows or system directories."
        )

    # Only direct files are organized. Existing category folders and
    # files inside subfolders are left untouched.
    files = [item for item in source.iterdir() if item.is_file()]

    total = len(files)
    moved = 0
    skipped = 0
    errors = []

    for index, file_path in enumerate(files, start=1):
        try:
            # Decide where this file belongs from its extension.
            category = category_for(file_path.suffix)

            # Create and validate the destination category folder.
            destination_folder = safe_category_folder(source, category)

            # Find a collision-safe destination before moving anything.
            destination = unique_destination(
                destination_folder / file_path.name
            )

            # Move the file. Existing files are never overwritten.
            original_name = file_path.name
            shutil.move(str(file_path), str(destination))
            moved += 1

            if destination.name != original_name:
                message = (
                    f"Renamed {original_name} -> {destination.name} "
                    f"and moved to {category}"
                )
            else:
                message = f"Moved {original_name} -> {category}"

            if status_callback:
                status_callback(message)

        except (OSError, shutil.Error) as error:
            # One bad file should not stop all the other files.
            skipped += 1
            errors.append(f"Could not move '{file_path.name}': {error}")

        # Update progress after every file, including skipped files.
        percent = int(index / total * 100) if total else 100

        if progress_callback:
            progress_callback(percent)

    log_file = None

    # Save non-fatal file errors for troubleshooting without showing
    # technical details to the normal user.
    if errors:
        log_file = write_log(
            "File operation errors",
            "\n".join(errors),
        )

    return {
        "total": total,
        "moved": moved,
        "skipped": skipped,
        "errors": errors,
        "log_file": str(log_file) if log_file else None,
    }


# ============================================================
# BACKGROUND WORKER
# ============================================================
# QThread is the "background robot" described in the project
# blueprint. The GUI thread remains available to repaint the window
# while this worker handles file operations.
#
# Signals are the "walkie-talkies" between the background worker and
# the GUI: progress, status, completion, and failure information.
# ============================================================

class PeanutWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, source):
        super().__init__()
        self.source = FilePath(source)

    def run(self):
        try:
            result = organize_folder(
                self.source,
                progress_callback=self.progress.emit,
                status_callback=self.status.emit,
            )
            self.completed.emit(result)
        except Exception:
            details = traceback.format_exc()
            write_log("Fatal organization error", details)
            self.failed.emit(details)


# ============================================================
# MAIN APPLICATION WINDOW
# ============================================================
# The GUI is deliberately built from small screens so the user only
# sees the information needed at each step (progressive disclosure).
# ============================================================

class PeanutApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.selected_folder = None
        self.worker = None

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(760, 520)
        self.setStyleSheet(APP_STYLE)

        # QStackedWidget lets Peanut move through a simple workflow
        # without opening multiple windows.
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.build_welcome()
        self.build_folder_screen()
        self.build_ready_screen()
        self.build_progress_screen()
        self.build_result_screen()

        self.stack.setCurrentWidget(self.welcome_page)

    # --------------------------------------------------------
    # Reusable UI helpers
    # --------------------------------------------------------
    # These helpers keep spacing and styling consistent throughout
    # the application.

    def make_card(self):
        card = QFrame()
        card.setObjectName("card")
        return card

    def make_title(self, text):
        label = QLabel(text)
        label.setObjectName("title")
        label.setWordWrap(True)
        return label

    def make_subtitle(self, text):
        label = QLabel(text)
        label.setObjectName("subtitle")
        label.setWordWrap(True)
        return label

    # --------------------------------------------------------
    # Welcome screen
    # --------------------------------------------------------
    # Give a first-time user a simple explanation before asking them
    # to choose anything.

    def build_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(80, 70, 80, 70)
        layout.setSpacing(18)

        layout.addStretch()
        layout.addWidget(self.make_title("Welcome to Peanut"))
        layout.addWidget(
            self.make_subtitle(
                "Clean up a messy folder in a few clicks. "
                "Choose a folder and Peanut will sort its files into clear categories."
            )
        )

        card = self.make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 22, 26, 22)
        card_layout.addWidget(QLabel("How it works"))
        card_layout.addWidget(
            self.make_subtitle(
                "1. Choose a folder\n"
                "2. Review what Peanut will do\n"
                "3. Organize your files\n"
                "4. See the results"
            )
        )
        layout.addWidget(card)

        button = QPushButton("Get Started")
        button.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.folder_page)
        )
        layout.addWidget(button)

        layout.addStretch()

        self.welcome_page = page
        self.stack.addWidget(page)

    # --------------------------------------------------------
    # Folder-selection screen
    # --------------------------------------------------------
    # This is where the user selects the folder to organize.
    # Protected folders are rejected immediately for clearer UX,
    # while the worker also checks again before doing any work.

    def build_folder_screen(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(80, 70, 80, 70)
        layout.setSpacing(18)

        layout.addWidget(self.make_title("Choose a folder"))
        layout.addWidget(
            self.make_subtitle(
                "Pick the folder you want to organize. "
                "Your files stay on your computer."
            )
        )

        self.folder_card = self.make_card()
        card_layout = QVBoxLayout(self.folder_card)
        card_layout.setContentsMargins(26, 24, 26, 24)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setObjectName("muted")
        self.folder_label.setWordWrap(True)
        card_layout.addWidget(self.folder_label)

        layout.addWidget(self.folder_card)

        choose = QPushButton("Choose Folder")
        choose.clicked.connect(self.choose_folder)
        layout.addWidget(choose)

        self.folder_next = QPushButton("Continue")
        self.folder_next.setEnabled(False)
        self.folder_next.clicked.connect(self.show_ready)
        layout.addWidget(self.folder_next)

        back = QPushButton("Back")
        back.setObjectName("secondary")
        back.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.welcome_page)
        )
        layout.addWidget(back)

        layout.addStretch()

        self.folder_page = page
        self.stack.addWidget(page)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose a folder to organize",
            str(FilePath.home()),
        )

        if not folder:
            return

        selected = FilePath(folder).resolve()

        # Do an immediate safety check before enabling Continue.
        if is_forbidden_source(selected):
            QMessageBox.warning(
                self,
                "Folder not allowed",
                "Peanut cannot organize protected Windows or system folders.\n\n"
                "Please choose a normal working folder such as Downloads, "
                "Documents, Desktop, or another personal folder.",
            )
            return

        self.selected_folder = selected
        self.folder_label.setText(str(selected))
        self.folder_next.setEnabled(True)

    # --------------------------------------------------------
    # Ready screen
    # --------------------------------------------------------
    # Show a simple preview before the user commits to moving files.

    def show_ready(self):
        if not self.selected_folder:
            return

        try:
            file_count = sum(
                1 for item in self.selected_folder.iterdir() if item.is_file()
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Folder could not be read",
                f"Peanut could not inspect this folder.\n\n{error}",
            )
            return

        self.ready_label.setText(
            f"You selected:\n{self.selected_folder}\n\n"
            f"Files found: {file_count}\n\n"
            "When you click Organize Files, Peanut will sort direct files "
            "into Images, Videos, Documents, Audio, Archives, Code, CAD, "
            "or Others. Existing filenames are protected from overwrite."
        )
        self.stack.setCurrentWidget(self.ready_page)

    def build_ready_screen(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(80, 70, 80, 70)
        layout.setSpacing(18)

        layout.addWidget(self.make_title("Ready to organize?"))

        card = self.make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 24)

        self.ready_label = QLabel()
        self.ready_label.setObjectName("subtitle")
        self.ready_label.setWordWrap(True)
        card_layout.addWidget(self.ready_label)

        layout.addWidget(card)

        organize = QPushButton("Organize Files")
        organize.clicked.connect(self.start_organizing)
        layout.addWidget(organize)

        back = QPushButton("Choose Another Folder")
        back.setObjectName("secondary")
        back.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.folder_page)
        )
        layout.addWidget(back)

        layout.addStretch()

        self.ready_page = page
        self.stack.addWidget(page)

    # --------------------------------------------------------
    # Progress screen
    # --------------------------------------------------------
    # The progress screen is intentionally simple. The worker sends
    # progress and status updates while the GUI remains responsive.

    def build_progress_screen(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(80, 90, 80, 90)
        layout.setSpacing(18)

        layout.addWidget(self.make_title("Organizing your files..."))

        self.status_label = self.make_subtitle("Starting...")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_page = page
        self.stack.addWidget(page)

    # --------------------------------------------------------
    # Result screen
    # --------------------------------------------------------
    # Give the user a plain-English summary rather than exposing
    # internal Python details.

    def build_result_screen(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(80, 70, 80, 70)
        layout.setSpacing(18)

        self.result_title = self.make_title("All done")
        layout.addWidget(self.result_title)

        self.result_label = self.make_subtitle("")
        layout.addWidget(self.result_label)

        self.result_details = QLabel("")
        self.result_details.setObjectName("muted")
        self.result_details.setWordWrap(True)
        layout.addWidget(self.result_details)

        again = QPushButton("Organize Another Folder")
        again.clicked.connect(self.reset_to_folder_selection)
        layout.addWidget(again)

        exit_button = QPushButton("Close")
        exit_button.setObjectName("secondary")
        exit_button.clicked.connect(self.close)
        layout.addWidget(exit_button)

        layout.addStretch()

        self.result_page = page
        self.stack.addWidget(page)

    # --------------------------------------------------------
    # Start the background operation
    # --------------------------------------------------------
    # The UI creates a worker thread instead of performing the move
    # loop directly inside a button-click handler.

    def start_organizing(self):
        if not self.selected_folder:
            return

        # Re-check the folder immediately before touching files.
        if is_forbidden_source(self.selected_folder):
            QMessageBox.warning(
                self,
                "Folder not allowed",
                "This folder is protected and cannot be organized by Peanut.",
            )
            return

        self.progress_bar.setValue(0)
        self.status_label.setText("Preparing...")
        self.stack.setCurrentWidget(self.progress_page)

        # Create the background worker using the selected folder.
        self.worker = PeanutWorker(self.selected_folder)

        # Connect the worker's signals to the UI.
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.completed.connect(self.show_results)
        self.worker.failed.connect(self.show_error)

        # Start the worker thread.
        self.worker.start()

    # --------------------------------------------------------
    # Completion handling
    # --------------------------------------------------------
    # Convert the engine result into a user-friendly summary.

    def show_results(self, result):
        self.result_title.setText("All done")

        if result["total"] == 0:
            self.result_title.setText("Nothing to organize")
            self.result_label.setText(
                "Peanut didn't find any files in this folder."
            )
        elif result["skipped"]:
            self.result_label.setText(
                f"{result['moved']} file(s) organized. "
                f"{result['skipped']} file(s) skipped."
            )
        else:
            self.result_label.setText(
                f"{result['moved']} file(s) organized successfully."
            )

        details = f"Files found: {result['total']}\n"
        details += f"Files moved: {result['moved']}\n"
        details += f"Files skipped: {result['skipped']}"

        if result["errors"]:
            details += "\n\nSome files could not be moved:\n"
            details += "\n".join(
                f"- {message}" for message in result["errors"][:8]
            )

            if len(result["errors"]) > 8:
                details += f"\n- ...and {len(result['errors']) - 8} more."

            if result["log_file"]:
                details += (
                    "\n\nTechnical details were saved to:\n"
                    f"{result['log_file']}"
                )

        self.result_details.setText(details)
        self.stack.setCurrentWidget(self.result_page)

        # The thread has completed its task; it can now be released.
        if self.worker is not None:
            self.worker.deleteLater()

    # --------------------------------------------------------
    # Fatal-error handling
    # --------------------------------------------------------
    # A fatal problem is shown in plain language. Detailed Python
    # traceback information is logged instead of overwhelming the user.

    def show_error(self, details):
        log_file = write_log("GUI-visible organization failure", details)

        self.stack.setCurrentWidget(self.ready_page)

        message = (
            "Peanut could not complete the operation.\n\n"
            "No further files were processed after the problem occurred."
        )

        if log_file:
            message += f"\n\nTechnical details were saved to:\n{log_file}"

        QMessageBox.critical(
            self,
            "Something went wrong",
            message,
        )

    # --------------------------------------------------------
    # Reset workflow
    # --------------------------------------------------------
    # Clear the previous selection so a new run starts cleanly.

    def reset_to_folder_selection(self):
        self.selected_folder = None
        self.folder_label.setText("No folder selected")
        self.folder_next.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")
        self.stack.setCurrentWidget(self.folder_page)

    # --------------------------------------------------------
    # Safe application closing
    # --------------------------------------------------------
    # Never allow the user to close the window while files are being
    # moved. Closing at that exact moment could interrupt file I/O.

    def closeEvent(self, event: QCloseEvent):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Peanut is still working",
                "Please wait for Peanut to finish organizing the files "
                "before closing the application.",
            )
            event.ignore()
            return

        event.accept()


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================
# This block starts the Qt application when the file is run directly.
# PyInstaller uses the same entry point when creating Peanut.exe.
# ============================================================

def main():
    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Peanut")

    window = PeanutApp()
    window.show()

    sys.exit(app.exec())


# Only start the graphical application when this file is executed
# directly, not when another Python file imports Peanut for testing.
if __name__ == "__main__":
    main()
