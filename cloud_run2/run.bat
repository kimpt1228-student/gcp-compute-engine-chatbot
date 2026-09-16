@echo off
chcp 65001 > nul
echo ======================================================
echo  Gemini Flash Chatbot Local Run (ADC Mode)
echo ======================================================

echo [1/2] Checking Python dependencies...
python -m pip install -r requirements.txt --quiet

echo [2/2] Checking Application Default Credentials (ADC)...
python -c "import google.auth; creds, p = google.auth.default(); print('[OK] ADC Credential Detected. Project:', p)" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] ADC credentials not found on your local PC.
    echo Please run the following command to login:
    echo    gcloud auth application-default login
    echo.
)

echo Starting local FastAPI server on http://localhost:8080 ...
python app.py
pause
