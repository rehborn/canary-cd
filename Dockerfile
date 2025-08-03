FROM python:3.13-alpine

ARG SRC=canary_cd

ENV LOGLEVEL=INFO
ENV APP_DIR=/app
ENV DATA_DIR=/data

RUN apk add curl git openssh-keygen openssh-client-default docker-cli-compose --no-cache

WORKDIR ${APP_DIR}
COPY pyproject.toml uv.lock ${APP_DIR}
RUN pip install uv --root-user-action=ignore && uv sync --locked


ADD $SRC ${APP_DIR}/$SRC

EXPOSE 80

CMD ["uv", "run", "uvicorn", "canary_cd.main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
