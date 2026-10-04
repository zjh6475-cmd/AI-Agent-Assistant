# syntax=docker/dockerfile:1

# 使用与当前本地环境相同的大版本 Python，slim 保持基础镜像较小。
FROM python:3.12-slim

# 后续命令都在容器内的 /app 目录执行。
WORKDIR /app

# 先只复制依赖清单，让“依赖安装”能使用 Docker 缓存。
# 日常只改业务代码时，不必重复安装全部 Python 包。
COPY requirements.txt ./

# 下载缓存只保存在 BuildKit 构建缓存，不会写入最终镜像。
# requirements.txt 变更后可复用已下载的 wheel，加快重新构建。
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 复制后端业务代码；.dockerignore 已排除密钥与用户数据。
COPY . .

# 让 Python 日志直接输出，方便以后通过 Docker 查看运行日志。
ENV PYTHONUNBUFFERED=1

# 说明后端服务使用 8000 端口。
EXPOSE 8000

# 生产环境不使用 --reload，并监听所有容器网络地址。
# Nginx 可通过 backend:8000 访问它。
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]