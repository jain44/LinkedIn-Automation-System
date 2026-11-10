@echo off
title Jainam Jain - Tech Internship LinkedIn Automation
cls

echo =================================================================
echo        JAINAM JAIN - TECH INTERNSHIP OUTREACH AUTOMATION
echo =================================================================
echo.
echo Select an option:
echo   [1] Dry Run (Scrape LinkedIn + Preview Emails, NO real emails sent)
echo   [2] Live Outreach (Scrape LinkedIn + SEND REAL EMAILS via Gmail)
echo   [3] Test Gmail Connection & Setup
echo   [4] Preview Cold Email Templates
echo   [5] Send to Existing Unsent Leads (Skip Scraping)
echo   [6] Exit
echo.
set /p choice="Enter choice (1-6): "

if "%choice%"=="1" (
    cls
    echo Starting Dry Run...
    python main.py
    pause
    goto :eof
)

if "%choice%"=="2" (
    cls
    echo Starting Live Outreach...
    python main.py --send
    pause
    goto :eof
)

if "%choice%"=="3" (
    cls
    echo Testing Gmail SMTP & Setup...
    python test_connection.py
    pause
    goto :eof
)

if "%choice%"=="4" (
    cls
    echo Generating Email Previews...
    python preview_emails.py
    pause
    goto :eof
)

if "%choice%"=="5" (
    cls
    echo Sending to existing pending leads...
    python main.py --skip-scrape --send
    pause
    goto :eof
)

if "%choice%"=="6" (
    exit
)

echo Invalid choice.
pause
