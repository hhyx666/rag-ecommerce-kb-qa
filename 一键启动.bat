@echo off
chcp 936 >nul
title 一键启动 - RAG电商知识库问答系统

echo ============================================
echo   RAG 电商知识库问答系统 - 一键启动
echo ============================================
echo.

REM 检查 Ollama 大模型服务是否在运行,没运行就自动启动
curl -s -o nul --max-time 2 http://127.0.0.1:11434/api/tags
if errorlevel 1 goto start_llm
echo [1/3] Ollama 大模型服务已在运行
goto llm_ok

:start_llm
echo [1/3] 启动 Ollama 大模型服务(模型在D盘)...
start "Ollama大模型" cmd /k "set OLLAMA_MODELS=D:\AIModels\ollama && C:\Users\ROG\AppData\Local\Programs\Ollama\ollama.exe serve"
timeout /t 4 /nobreak >nul

:llm_ok
echo [2/3] 启动后端服务(端口8001)...
start "后端服务" cmd /k "cd /d C:\Users\ROG\Desktop\vibe学习\langchain项目\backend && D:\venvs\langchain-project\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001"

echo [3/3] 启动前端页面(端口5173)...
start "前端页面" cmd /k "cd /d C:\Users\ROG\Desktop\vibe学习\langchain项目\frontend && npm run dev"

echo.
echo 等待 12 秒让服务启动起来...
timeout /t 12 /nobreak >nul
echo 正在打开浏览器...
start "" http://localhost:5173
echo.
echo ============================================
echo  启动完成!浏览器已打开系统页面。
echo  管理员账号: admin   密码: 123456
echo.
echo  提示: 另外三个窗口(大模型/后端/前端)在干活,
echo        这个窗口可以关闭,那三个别关。
echo ============================================
pause
