@echo off
title Jainam Outreach Reminder Engine
cd /d "%~dp0"

echo ======================================================================
echo    JAINAM JAIN - AUTOMATED OUTREACH REMINDERS & REPLY DETECTOR
echo ======================================================================
echo.
echo Choose an option:
echo [1] Preview eligible reminders (Default: 3 days threshold, dry run)
echo [2] Send LIVE reminder emails to eligible unreplied recruiters
echo [3] Check Gmail inbox for recruiter replies (Status Report)
echo [4] Preview reminders for 2 days threshold
echo [5] Exit
echo.

set /p choice="Enter choice (1-5): "

if "%choice%"=="1" (
    python send_reminders.py
) else if "%choice%"=="2" (
    python send_reminders.py --send
) else if "%choice%"=="3" (
    python send_reminders.py --check-replies
) else if "%choice%"=="4" (
    python send_reminders.py --days 2
) else (
    echo Exiting...
)

echo.
pause
