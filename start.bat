@echo off

python -m venv venv
call venv\Scripts\activate.bat
@REM python -m pip install --upgrade pip
@REM python -m pip install -U setuptools
@REM python -m pip install -r requirements.txt

echo Running ScenarioAI...

python main.py

pause