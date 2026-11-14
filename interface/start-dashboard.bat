@echo off
title Credit Risk Lab
echo Starting the local research dashboard in Ubuntu WSL...
echo Open http://localhost:8000 after the server starts.
wsl.exe --cd "%~dp0." --exec /bin/bash ./start.sh
pause
