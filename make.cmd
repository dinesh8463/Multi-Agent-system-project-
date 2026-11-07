@echo off
rem Windows task adapter. On POSIX use GNU make with the supplied Makefile.
if "%1"=="test" .venv\Scripts\python.exe -m pytest -q
if "%1"=="demo" .venv\Scripts\python.exe -m swarm.experiments.run_all --demo
if "%1"=="all" .venv\Scripts\python.exe -m swarm.experiments.run_all
if "%1"=="verify" .venv\Scripts\python.exe -m swarm.experiments.verify
exit /b %errorlevel%
