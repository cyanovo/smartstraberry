# https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/docker/china/Dockerfile
# Use DaoCloud mirrored vllm image for China region for gpu with Volta、Turing、Ampere、Ada Lovelace、Hopper、Blackwell architecture (7.0 <= Compute Capability <= 12.0)
# Compute Capability version query (https://developer.nvidia.com/cuda-gpus)
# support x86_64 architecture and ARM(AArch64) architecture
ARG MINERU_BASE_IMAGE=registry.strawberry.lan:5000/daocloud/vllm-openai:v0.11.2
FROM ${MINERU_BASE_IMAGE}

ARG APT_PROXY=http://apt.strawberry.lan:3142
ARG PYPI_INDEX_URL=http://pypi.strawberry.lan:8088/simple
ARG PYPI_FALLBACK_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ARG PYPI_TRUSTED_HOST=pypi.strawberry.lan

# Install libgl for opencv support & Noto fonts for Chinese characters
RUN set -ex && \
    if [ -n "$APT_PROXY" ]; then echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/01cyanproxy; fi && \
    (apt-get -o Acquire::Retries=10 -o Acquire::http::Pipeline-Depth=0 update || (rm -f /etc/apt/apt.conf.d/01cyanproxy && apt-get update)) && \
    (apt-get -o Acquire::Retries=10 -o Acquire::http::Pipeline-Depth=0 install -y \
        fonts-noto-core \
        fonts-noto-cjk \
        fontconfig \
        libgl1 \
        || (rm -f /etc/apt/apt.conf.d/01cyanproxy && apt-get update && apt-get install -y fonts-noto-core fonts-noto-cjk fontconfig libgl1)) && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install mineru latest
RUN python3 -m pip install -U 'mineru[core]>=3.0.0' -i ${PYPI_INDEX_URL} --trusted-host ${PYPI_TRUSTED_HOST} --break-system-packages \
    || python3 -m pip install -U 'mineru[core]>=3.0.0' -i ${PYPI_FALLBACK_INDEX_URL} --break-system-packages && \
    python3 -m pip cache purge

# Download models and update the configuration file
RUN /bin/bash -c "mineru-models-download -s modelscope -m all"

# Set the entry point to activate the virtual environment and run the command line tool
ENTRYPOINT ["/bin/bash", "-c", "export MINERU_MODEL_SOURCE=local && exec \"$@\"", "--"]
