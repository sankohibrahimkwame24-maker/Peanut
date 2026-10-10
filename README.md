# Peanut V2 - Final Production Build

Peanut is a small Windows desktop utility that organizes the direct files inside a selected folder into clear categories.

This is the **final V2 product build**. V1 proved the organizer logic as a Python script. V2 turns that idea into a production-style desktop application with a GUI, safety controls, background processing, duplicate protection, error reporting, logging, and Windows packaging support.

## What is included

- `peanut.py` - final Peanut V2 source code
- `test_peanut_v2.py` - automated release test suite
- `requirements.txt` - runtime and packaging dependencies
- `build_peanut.bat` - Windows build/test script
- `Peanut_V2_Code_Explained_Line_By_Line.pdf` - beginner-friendly code explanation

## Final V2 features

### File organization

Peanut recognizes:

- Images
- Videos
- Audio
- Documents
- Archives
- Code
- CAD
- Others

Unknown extensions are moved to `Others` instead of being guessed.

### Safety

Peanut refuses to organize filesystem roots and protected Windows/application directories such as the Windows system directory, Program Files, ProgramData, and related shared program directories.

The source path is resolved before the operation so the safety check is based on the actual destination of links/junctions rather than only the path text the user sees.

Category folders are also checked to make sure a destination cannot escape the selected source folder through a symbolic link.

### Duplicate protection

Peanut never intentionally overwrites an existing file.

Example:

```text
report.pdf
report (1).pdf
report (2).pdf
```

### Failure handling

A single inaccessible or locked file is skipped and reported while other files continue to be processed.

Technical failure details are written to a Peanut log instead of exposing a Python traceback to a normal user.

### Responsive GUI

The file engine runs in `QThread`. The GUI receives progress and status updates through Qt signals, so the application can keep responding while file operations run.

### User experience

The normal workflow is:

1. Get Started
2. Choose Folder
3. Review the selection and file count
4. Organize Files
5. See the result summary

The interface uses layout managers instead of hard-coded screen coordinates, which helps it adapt to different window sizes and display scaling.

## Why the architecture is split into an engine and a GUI

The final source contains a function named `organize_folder()` that holds the real file-management logic.

`PeanutWorker` runs that engine in a background thread.

`PeanutApp` is responsible for the user interface.

This separation makes the project easier to test, maintain, debug, and package.

## Development decisions from the provided Peanut documents

The provided Peanut Development Guide and Master Development Blueprint identified these production risks and design requirements:

- duplicate-name data loss
- locked/open-file `PermissionError`
- dangerous system/root paths
- hard-coded user paths
- frozen GUI when file work runs on the main thread
- fixed-size UI problems on different displays
- packaging and SmartScreen/antivirus considerations
- progressive disclosure and consistent native-style UI

Those points are incorporated into this final V2 source rather than being left for another version.

## Install and run from source on Windows

Use a recent Python installation from python.org rather than the Microsoft Store build for PySide6 development.

Open Command Prompt in the Peanut project folder:

```bat
py -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python peanut.py
```

## Automated release testing

After activating the virtual environment:

```bat
python test_peanut_v2.py
```

The suite checks:

1. file classification
2. duplicate-name protection
3. unknown extension handling
4. empty folder handling
5. simulated file-access failure and continuation
6. 1,000-file stress test
7. repeat-run behavior
8. protected root/system path safety

The test suite uses temporary folders and does not organize real user folders.

## Manual release check

Once the automated tests pass, make one disposable folder such as `Desktop\\Peanut_Test` and put copied test files inside it.

Run the GUI and verify:

- the folder picker works
- the ready screen shows the selected path and file count
- the progress bar updates
- the result screen shows moved/skipped counts
- duplicate files are renamed instead of overwritten
- the application does not close while the worker is running

Then run the application a second time on the same test folder. There should be no chaos and no repeated movement of files inside the category folders.

## Build Peanut.exe

The included `build_peanut.bat` script:

1. creates an isolated virtual environment if needed
2. installs the dependencies
3. runs the automated tests
4. builds a test one-folder executable
5. builds the final single-file `Peanut.exe`

Run:

```bat
build_peanut.bat
```

The final executable is created at:

```text
_dist_release\\Peanut.exe
```

## Packaging notes

PyInstaller can produce a standalone executable so the end user does not need Python installed. PyInstaller documents `--onefile` and `--windowed` for single-file GUI applications.

For troubleshooting, a one-folder build is easier to diagnose than a one-file build. Qt for Python's deployment documentation also recommends building in the intended Python environment so the correct PySide6 installation is bundled.

A Windows security warning can still appear for an unsigned executable. This is a distribution/signing issue, not evidence that the Peanut source code is malware. An eventual public commercial release should consider code signing.

## Important release limitation

The development environment used to prepare this source is not Windows and does not have the PySide6 runtime installed, so the Windows GUI and `.exe` cannot honestly be declared fully verified from this environment.

The core file engine **has been executed here with a controlled PySide6 stub and passed its 1,000-file stress test**. The final Windows verification must be run on the target Windows machine using the real PySide6 installation and the produced `Peanut.exe`.

## External research used for deployment

The final packaging approach was checked against current official documentation:

- Qt for Python - PyInstaller deployment: https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html
- PyInstaller - operating mode: https://pyinstaller.org/en/stable/operating-mode.html
- PyInstaller - usage: https://www.pyinstaller.org/en/stable/usage.html
- Qt for Python - Windows: https://doc.qt.io/qtforpython-6/building_from_source/windows.html

## Learning rule for this project

The source code is intentionally heavily commented.

Every important feature has a nearby `#` explanation describing its purpose, and the separate code-explanation PDF walks through the source line by line in beginner-friendly language.

That means the final product is not just a piece of code to copy. It is also a project you can study and maintain.
