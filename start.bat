@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==============================================
echo   多工具智能体 · 一键启动
echo ==============================================
echo.

REM ---- 1. 检查 .env ----
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [!] 首次运行：已为你创建 .env 文件。
    echo     请用记事本打开 .env，把 DEEPSEEK_API_KEY 后面的占位符换成你的真实 Key，
    echo     保存后再重新运行本脚本。
    echo.
    pause
    exit /b 1
)

REM ---- 2. 检查依赖 ----
python -c "import fastapi, streamlit, openai, dotenv" >nul 2>&1
if errorlevel 1 (
    echo [*] 正在安装依赖（首次会下载一会儿）...
    python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
    if errorlevel 1 (
        echo.
        echo [X] 依赖安装失败。请检查 Python 环境后手动执行：
        echo     python -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
)

REM ---- 3. 选择启动方式 ----
echo.
echo 请选择启动方式：
echo   [1] 网页版（推荐，浏览器里对话，看得见思考过程）
echo   [2] API 服务（FastAPI，供程序调用）
echo.
set /p choice=请输入 1 或 2 后回车：

if "%choice%"=="1" (
    echo.
    echo [*] 启动网页版，浏览器会自动打开 http://localhost:8501
    python -m streamlit run app.py
) else if "%choice%"=="2" (
    echo.
    echo [*] 启动 API 服务，接口文档见 http://127.0.0.1:8000/docs
    python -m uvicorn api:app --host 0.0.0.0 --port 8000
) else (
    echo [!] 输入无效，默认启动网页版。
    python -m streamlit run app.py
)

endlocal
