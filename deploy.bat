@echo off
set "SOURCE=%~dp0"
set "DEST=P:\ICane\projets\ICane\electronique\pnp_script"

echo ==========================================
echo [1/2] Pushing to Git Origin...
echo ==========================================
git push origin master
if %errorlevel% neq 0 (
    echo [ERROR] Git push failed. Deployment aborted.
    pause
    exit /b %errorlevel%
)

echo.
echo ==========================================
echo [2/2] Syncing to Machine (P: Drive)...
echo Source: %SOURCE%
echo Dest:   %DEST%
echo ==========================================
:: /MIR: Mirror directory tree (copy new/modified, delete extra in dest)
:: /XD: Exclude directories (.git, etc)
:: /XF: Exclude files (this script itself)
:: /FFT: Assume FAT file times (2-second granularity) - useful for network/pCloud drives
:: /R:3 /W:5: Retry 3 times, wait 5 seconds (network resilience)

robocopy "%SOURCE%." "%DEST%" /MIR /XD .git .vscode .idea __pycache__ /XF deploy.bat /FFT /R:3 /W:5

:: Robocopy exit codes: 0-7 are success (0=No Change, 1=Copied, etc)
if %errorlevel% geq 8 (
    echo [ERROR] Robocopy failed with error code %errorlevel%.
) else (
    echo [SUCCESS] Deployment finished successfully.
)

pause
