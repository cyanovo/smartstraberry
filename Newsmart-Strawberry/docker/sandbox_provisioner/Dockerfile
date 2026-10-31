ARG PYTHON_BASE_IMAGE=registry.strawberry.lan:5000/library/python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG PYPI_INDEX_URL=http://pypi.strawberry.lan:8088/simple
ARG PYPI_FALLBACK_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ARG PYPI_TRUSTED_HOST=pypi.strawberry.lan

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt --index-url ${PYPI_INDEX_URL} --trusted-host ${PYPI_TRUSTED_HOST} \
    || pip install --no-cache-dir -r /app/requirements.txt --index-url ${PYPI_FALLBACK_INDEX_URL}

COPY app.py /app/app.py

EXPOSE 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
