FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd -u 1000 -m appuser

COPY app ./app
COPY start.sh .
RUN mkdir -p /data \
    && chmod +x /srv/app/start.sh \
    && chown -R appuser:appuser /srv/app /data

USER appuser
