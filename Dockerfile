FROM python:3.12-slim-bullseye

WORKDIR /app

COPY requirements.txt /app

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install -r requirements.txt \
    && apt-get purge -y --auto-remove gcc libc-dev

COPY openproject_telegram /app/openproject_telegram

CMD ["python", "-m", "openproject_telegram.app"]
