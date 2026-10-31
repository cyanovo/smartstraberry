# 使用轻量级Python基础镜像（本地镜像站优先，.env 可覆盖）
ARG PYTHON_BASE_IMAGE=registry.strawberry.lan:5000/library/python:3.12-slim
ARG UV_IMAGE=registry.strawberry.lan:5000/ghcr/astral-sh/uv:0.7.2
ARG NODE_SLIM_IMAGE=registry.strawberry.lan:5000/library/node:24-slim
FROM ${UV_IMAGE} AS uv-bin
FROM ${NODE_SLIM_IMAGE} AS node-bin
FROM ${PYTHON_BASE_IMAGE}
COPY --from=uv-bin /uv /uvx /bin/
COPY --from=node-bin /usr/local/bin /usr/local/bin
COPY --from=node-bin /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-bin /usr/local/include /usr/local/include
COPY --from=node-bin /usr/local/share /usr/local/share

ARG APT_PROXY=http://apt.strawberry.lan:3142
ARG NPM_REGISTRY=http://npm.strawberry.lan:4873
ARG NPM_FALLBACK_REGISTRY=https://registry.npmmirror.com
ARG PYPI_BASE_URL=http://pypi.strawberry.lan:8088
ARG PYPI_INDEX_URL=http://pypi.strawberry.lan:8088/simple
ARG PYPI_FALLBACK_INDEX_URL=https://pypi.org/simple
ARG PYPI_TRUSTED_HOST=pypi.strawberry.lan

# 设置工作目录
WORKDIR /app

# 环境变量设置
ENV TZ=Asia/Shanghai \
    UV_PROJECT_ENVIRONMENT="/usr/local" \
    UV_COMPILE_BYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    UV_DEFAULT_INDEX=${PYPI_INDEX_URL} \
    UV_INDEX=${PYPI_INDEX_URL} \
    UV_INSECURE_HOST=${PYPI_TRUSTED_HOST} \
    PIP_INDEX_URL=${PYPI_INDEX_URL} \
    PIP_TRUSTED_HOST=${PYPI_TRUSTED_HOST}

# 设置 npm 镜像源，为 MCP 和 Skills 安装依赖
RUN npm config set registry ${NPM_REGISTRY} --global \
    || npm config set registry ${NPM_FALLBACK_REGISTRY} --global \
    && npm cache clean --force

# 设置代理和时区，安装系统依赖 - 合并为一个RUN减少层数
RUN set -ex \
    && if [ -n "$APT_PROXY" ]; then echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/01cyanproxy; fi \
    # (A) 设置时区
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    # (B) 安装必要的系统库
    && (apt-get -o Acquire::Retries=10 -o Acquire::http::Pipeline-Depth=0 update || (rm -f /etc/apt/apt.conf.d/01cyanproxy && apt-get update)) \
    && (apt-get -o Acquire::Retries=10 -o Acquire::http::Pipeline-Depth=0 install -y --no-install-recommends --fix-missing \
        curl \
        ffmpeg \
        git \
        libpq5 \
        libsm6 \
        libxext6 \
        libzbar0 \
        || (rm -f /etc/apt/apt.conf.d/01cyanproxy && apt-get update && apt-get install -y --no-install-recommends --fix-missing curl ffmpeg git libpq5 libsm6 libxext6 libzbar0)) \
    # (C) 清理垃圾，减小体积
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制项目配置文件（context 为项目根目录，故用 backend/ 而非 ../backend/）
COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/.python-version /app/.python-version
COPY backend/uv.lock /app/uv.lock
RUN cp /app/pyproject.toml /app/pyproject.toml.fallback \
    && cp /app/uv.lock /app/uv.lock.fallback \
    && sed -i 's|https://pypi.tuna.tsinghua.edu.cn/simple|https://pypi.org/simple|g' /app/pyproject.toml.fallback /app/uv.lock.fallback \
    && sed -i 's|https://pypi.tuna.tsinghua.edu.cn/packages|https://files.pythonhosted.org/packages|g' /app/uv.lock.fallback \
    && sed -i "s|https://pypi.tuna.tsinghua.edu.cn/packages|${PYPI_BASE_URL}/mirror/pypi/packages|g" /app/uv.lock \
    && sed -i "s|https://files.pythonhosted.org/packages|${PYPI_BASE_URL}/mirror/files-pythonhosted/packages|g" /app/uv.lock \
    && sed -i "s|https://download-r2.pytorch.org/whl/cpu|${PYPI_BASE_URL}/mirror/pytorch-r2/whl/cpu|g" /app/uv.lock \
    && sed -i "s|https://download.pytorch.org/whl/cpu|${PYPI_BASE_URL}/mirror/pytorch/whl/cpu|g" /app/uv.lock \
    && sed -i "s|https://pypi.tuna.tsinghua.edu.cn/simple|${PYPI_INDEX_URL}|g" /app/pyproject.toml /app/uv.lock \
    && sed -i "s|https://download.pytorch.org/whl/cpu|${PYPI_INDEX_URL}|g" /app/pyproject.toml /app/uv.lock

# 先复制 package 目录，因为 pyproject.toml 中 yuxi = { path = "package", editable = true }
COPY backend/package /app/package
RUN cp /app/package/pyproject.toml /app/package/pyproject.toml.fallback \
    && sed -i 's|https://pypi.tuna.tsinghua.edu.cn/simple|https://pypi.org/simple|g' /app/package/pyproject.toml.fallback \
    && sed -i "s|https://pypi.tuna.tsinghua.edu.cn/simple|${PYPI_INDEX_URL}|g" /app/package/pyproject.toml \
    && sed -i "s|https://download.pytorch.org/whl/cpu|${PYPI_INDEX_URL}|g" /app/package/pyproject.toml

# 依赖安装：优先走本地镜像站；失败时回退到官方源
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --group test --no-dev --frozen \
    || (cp /app/pyproject.toml.fallback /app/pyproject.toml \
        && cp /app/uv.lock.fallback /app/uv.lock \
        && cp /app/package/pyproject.toml.fallback /app/package/pyproject.toml \
        && UV_DEFAULT_INDEX=${PYPI_FALLBACK_INDEX_URL} UV_INDEX=${PYPI_FALLBACK_INDEX_URL} uv sync --group test --no-dev --frozen)

# IoT MQTT 客户端依赖 + 视觉检测依赖（pyproject.toml 已声明，此处为容器内保底安装）
RUN pip install --no-cache-dir paho-mqtt ultralytics \
    || pip install --no-cache-dir paho-mqtt ultralytics --index-url ${PYPI_FALLBACK_INDEX_URL}

# 激活虚拟环境并添加到PATH
ENV PATH="/app/.venv/bin:$PATH"

# 复制 server 代码
COPY backend/server /app/server
