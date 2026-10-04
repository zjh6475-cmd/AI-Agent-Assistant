# syntax=docker/dockerfile:1

# 第一阶段：使用 Node 安装依赖并构建 Vite 静态文件。
FROM node:20-alpine AS build

WORKDIR /app

# 先复制锁文件；业务代码变化时可复用依赖安装层。
COPY package.json package-lock.json ./

# npm 下载缓存只保留在 BuildKit 中，不进入最终镜像。
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .

# Vite 会在构建时把该值写入浏览器代码。
# 浏览器请求 /api，后续由 Nginx 转发到 backend:8000。
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# 第二阶段：最终镜像只保留 Nginx 与构建后的 dist 文件。
FROM nginx:1.27-alpine AS production

# 下一步创建的 Nginx 配置负责静态文件、SPA 回退和 API 代理。
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80