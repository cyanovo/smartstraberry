# 开发阶段
ARG NODE_ALPINE_IMAGE=registry.strawberry.lan:5000/library/node:24-alpine
ARG NGINX_ALPINE_IMAGE=registry.strawberry.lan:5000/library/nginx:alpine
FROM ${NODE_ALPINE_IMAGE} AS development
WORKDIR /app
ENV TZ=Asia/Shanghai
ARG NPM_REGISTRY=http://npm.strawberry.lan:4873
ARG NPM_FALLBACK_REGISTRY=https://registry.npmmirror.com

# 安装与 packageManager 声明一致的 pnpm 版本，避免 latest 与锁文件格式不兼容
RUN npm install -g pnpm@10.11.0 --registry=${NPM_REGISTRY} \
    || npm install -g pnpm@10.11.0 --registry=${NPM_FALLBACK_REGISTRY}

# 复制 package.json 和 pnpm-lock.yaml
COPY ./web/package*.json ./
COPY ./web/pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --frozen-lockfile --registry=${NPM_REGISTRY} \
    || pnpm install --frozen-lockfile --registry=${NPM_FALLBACK_REGISTRY}

# 复制源代码
COPY ./web .

# 暴露端口
EXPOSE 5173

# 启动开发服务器的命令在 docker-compose 文件中定义

# 生产阶段
FROM ${NODE_ALPINE_IMAGE} AS build-stage
WORKDIR /app
ARG NPM_REGISTRY=http://npm.strawberry.lan:4873
ARG NPM_FALLBACK_REGISTRY=https://registry.npmmirror.com

# 安装与 packageManager 声明一致的 pnpm 版本
RUN npm install -g pnpm@10.11.0 --registry=${NPM_REGISTRY} \
    || npm install -g pnpm@10.11.0 --registry=${NPM_FALLBACK_REGISTRY}

# 复制依赖文件
COPY ./web/package*.json ./
COPY ./web/pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --frozen-lockfile --registry=${NPM_REGISTRY} \
    || pnpm install --frozen-lockfile --registry=${NPM_FALLBACK_REGISTRY}

# 复制源代码并构建
COPY ./web .
RUN pnpm run build

# 生产环境运行阶段
FROM ${NGINX_ALPINE_IMAGE} AS production
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY ./docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./docker/nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
