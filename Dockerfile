
# 多工具智能体 · FastAPI 后端镜像
#   构建：docker build -t agent-api .
#   运行：docker run -p 8000:8000 -e DEEPSEEK_API_KEY=sk-xxx agent-api

FROM python:3.11-slim

# 让容器里的 Python 更"干净"：
#   PYTHONUNBUFFERED=1         日志不缓冲，容器里能实时看到输出
#   PYTHONDONTWRITEBYTECODE=1  不生成 __pycache__，镜像更小
#   PIP_NO_CACHE_DIR=1         pip 不写缓存，镜像更小
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 第一步只拷依赖文件：利用 Docker 层缓存，依赖没变时不会重复装
COPY requirements-api.txt .

# 装运行时依赖（-i 是阿里云镜像加速，海外构建可删掉 -i 那段）
RUN pip install -r requirements-api.txt -i https://mirrors.aliyun.com/pypi/simple/

# 第二步拷源码（key.txt / .env 已被 .dockerignore 排除，不会进镜像）
COPY . .

# 对外暴露 8000 端口
EXPOSE 8000

# 容器启动即跑 FastAPI（--host 0.0.0.0 才能在容器外访问）
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
