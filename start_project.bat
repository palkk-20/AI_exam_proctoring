@echo off
title SentinelAI - Online Exam Proctoring System
cd /d "%~dp0"
echo ========================================================
echo  Starting SentinelAI Online Exam Proctoring System...
echo ========================================================
echo  Student Portal:    http://127.0.0.1:8000
echo  Proctor Dashboard: http://127.0.0.1:8000/admin
echo ========================================================
python run.py
pause
