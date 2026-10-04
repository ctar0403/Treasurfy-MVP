FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY treasurfy ./treasurfy

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 treasurfy \
    && mkdir -p /data \
    && chown -R treasurfy:treasurfy /data

USER treasurfy

EXPOSE 8000

CMD ["uvicorn", "treasurfy.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
