#!/usr/bin/env bash
# 多工具智能体 · 一键启动（Linux / macOS）
set -e
cd "$(dirname "$0")"

echo "=============================================="
echo "  多工具智能体 · 一键启动"
echo "=============================================="
echo ""

# 1. 检查 .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[!] 首次运行：已为你创建 .env 文件。"
    echo "    请编辑 .env，把 DEEPSEEK_API_KEY 后面的占位符换成你的真实 Key，"
    echo "    保存后再重新运行本脚本。"
    echo ""
    exit 1
fi

# 2. 检查依赖
if ! python3 -c "import fastapi, streamlit, openai, dotenv" >/dev/null 2>&1; then
    echo "[*] 正在安装依赖（首次会下载一会儿）..."
    python3 -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
fi

# 3. 选择启动方式
echo ""
echo "请选择启动方式："
echo "  [1] 网页版（推荐，浏览器里对话，看得见思考过程）"
echo "  [2] API 服务（FastAPI，供程序调用）"
echo ""
read -r -p "请输入 1 或 2 后回车：" choice

case "$choice" in
    1) echo "[*] 启动网页版 http://localhost:8501"; python3 -m streamlit run app.py ;;
    2) echo "[*] 启动 API http://127.0.0.1:8000/docs"; python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 ;;
    *) echo "[!] 输入无效，默认启动网页版。"; python3 -m streamlit run app.py ;;
esac
