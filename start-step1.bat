@echo off
echo Starting OpenJarvis Step 1...
echo.

REM Set environment variables
set ENABLE_LOCAL_OLLAMA=false
set ENABLE_STEP_1_BASIC_COMMANDS=true
set ENABLE_LOCAL_APP_OPENING=true
set ENABLE_STEP_2_BROWSER_SEARCH=true
set ENABLE_LOCAL_WEBSITE_OPENING=true
set ENABLE_LOCAL_BROWSER_SEARCH=true
set ENABLE_STEP_3_FILE_CREATION=true
set ENABLE_LOCAL_FILE_CREATION=true
set ENABLE_PERMISSION_SYSTEM=true
set ENABLE_HOSTED_SUPABASE=false
set ENABLE_OPENROUTER=true
set OPENROUTER_API_KEY=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
set OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
set OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free
set OPENROUTER_TIMEOUT_SECONDS=90
set OPENROUTER_MAX_RETRIES=2
set LLM_TEMPERATURE=0.2
set LLM_MAX_OUTPUT_TOKENS=2048
set MAX_AI_TOOL_CALLS=4
set ENABLE_STEP_4_NATURAL_LANGUAGE=true
set ENABLE_LOCAL_NATURAL_LANGUAGE_ROUTER=true
set ENABLE_STEP_5_AI_FALLBACK=true
set ENABLE_OPENROUTER_AI_FALLBACK=true
set ENABLE_AI_COMMAND_PLANNING=true
set LOCAL_NLU_CONFIDENCE_THRESHOLD=0.82

echo [1/2] Starting backend on http://127.0.0.1:8000 ...
start "OpenJarvis Backend" cmd /c "set ENABLE_LOCAL_OLLAMA=false && set ENABLE_STEP_1_BASIC_COMMANDS=true && set ENABLE_LOCAL_APP_OPENING=true && set ENABLE_STEP_2_BROWSER_SEARCH=true && set ENABLE_LOCAL_WEBSITE_OPENING=true && set ENABLE_LOCAL_BROWSER_SEARCH=true && set ENABLE_STEP_3_FILE_CREATION=true && set ENABLE_LOCAL_FILE_CREATION=true && set ENABLE_PERMISSION_SYSTEM=true && set ENABLE_HOSTED_SUPABASE=false && set ENABLE_OPENROUTER=true && set OPENROUTER_API_KEY=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 && set OPENROUTER_BASE_URL=https://openrouter.ai/api/v1 && set OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free && set OPENROUTER_TIMEOUT_SECONDS=90 && set OPENROUTER_MAX_RETRIES=2 && set LLM_TEMPERATURE=0.2 && set LLM_MAX_OUTPUT_TOKENS=2048 && set MAX_AI_TOOL_CALLS=4 && set ENABLE_STEP_4_NATURAL_LANGUAGE=true && set ENABLE_LOCAL_NATURAL_LANGUAGE_ROUTER=true && set ENABLE_STEP_5_AI_FALLBACK=true && set ENABLE_OPENROUTER_AI_FALLBACK=true && set ENABLE_AI_COMMAND_PLANNING=true && set LOCAL_NLU_CONFIDENCE_THRESHOLD=0.82 && python -m openjarvis.cli serve --step1-only --host 127.0.0.1 --port 8000"

REM Wait for backend to start
timeout /t 4 /nobreak >nul

echo [2/2] Starting frontend on http://localhost:5173 ...
cd /d C:\jarvis\veyra-openjarvis-base\frontend
start "OpenJarvis Frontend" cmd /c "npm run dev"

echo.
echo ========================================
echo   Both servers started!
echo   Frontend: http://localhost:5173
echo   Backend:  http://127.0.0.1:8000
echo ========================================
echo.
echo Open http://localhost:5173 in your browser
echo Press Ctrl+C in each window to stop
pause
