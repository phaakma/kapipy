@echo off
setlocal

SET "python_path=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe"
SET "python_file=changesets.py"
set "log_dir=%CD%\logs"
set "timestamp=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "logfile=%log_dir%\batch_logs_%timestamp%.log"

REM Create the logs directory if it doesn't exist
if not exist "%log_dir%" (
    mkdir "%log_dir%"
)

ECHO ========================================================
ECHO SCRIPT PATH = %CD%
ECHO.
ECHO python_path = %python_path%
ECHO python_file = %python_file%
ECHO arguments   = %*
ECHO ========================================================
ECHO.

"%python_path%" "%CD%\%python_file%" %* 1>> %logfile% 2>&1

endlocal