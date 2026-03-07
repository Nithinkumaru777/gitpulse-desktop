# GitPulse — Build Instructions

Follow these steps **in order** to create `GitPulse.exe`.

## Prerequisites
- **Python 3.10+** installed and in PATH
- **Git** installed and in PATH

## Step 1 — Install dependencies
```bash
pip install pillow pyinstaller
```

## Step 2 — Generate the icon
```bash
cd d:\PROJECTS\GreenGraph
python make_icon.py
```
This creates `gitpulse_icon.ico` in the same folder.

## Step 3 — Build the .exe
```bash
pyinstaller --noconsole --onefile --icon=gitpulse_icon.ico --name=GitPulse main.py
```

## Step 4 — Run it
Your standalone app is at:
```
d:\PROJECTS\GreenGraph\dist\GitPulse.exe
```
Move it to your Desktop and double-click to launch. No terminal window will appear.
