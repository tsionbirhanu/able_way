@echo off
rem Opens Mimi for a demo in Microsoft Edge with sound allowed before any click, so she starts
rem talking as soon as the page opens. Normal browser windows keep the usual rule (Chrome and Edge
rem hold sound until the learner first taps or presses a key) and Mimi shows a "Start Mimi" button.
rem
rem Start the servers first:   server\.venv\Scripts\python run.py
rem Then double-click this file (or run: open-demo.bat).
rem
rem A separate demo profile is used so the setting applies even if Edge is already open. Allow the
rem microphone once when Edge asks; the demo profile remembers it.

set "URL=http://localhost:8001/pages/concept-with-navigation.html"
set "PROFILE=%LOCALAPPDATA%\MimiDemoBrowser"

set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
  start "" "%EDGE%" --user-data-dir="%PROFILE%" --autoplay-policy=no-user-gesture-required --no-first-run "%URL%"
  exit /b 0
)

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
  start "" "%CHROME%" --user-data-dir="%PROFILE%" --autoplay-policy=no-user-gesture-required --no-first-run "%URL%"
  exit /b 0
)

echo Could not find Microsoft Edge or Google Chrome. Open %URL% in your browser and tap once.
pause
