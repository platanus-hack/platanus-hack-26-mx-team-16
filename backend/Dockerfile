FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS production_builder
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


#  P R O D U C T I O N
#
FROM python:3.13-slim-bookworm AS production

COPY --from=production_builder --chown=app:app /app /app
COPY --from=production_builder --chown=app:app /venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y bash curl gettext nginx build-essential libpq-dev python3-dev ca-certificates poppler-utils \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 libffi8 shared-mime-info fonts-dejavu-core \
    && curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | bash \
    && apt-get update && apt-get install -y infisical \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY docker/commands /commands
RUN sed -i 's/\r$//g' /commands
RUN chmod +x /commands

COPY docker/start-prod /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY run-script /run-script
RUN sed -i 's/\r$//g' /run-script
RUN chmod +x /run-script

CMD ["/start"]

#
#  D E V E L O P M E N T
#
FROM python:3.13-slim-bookworm AS development

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# poppler-utils (PDF tooling) + WeasyPrint's Pango/Cairo runtime libs so the
# report.pdf endpoint (PDF_ENGINE=weasyprint) renders locally too.
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 libffi8 shared-mime-info fonts-dejavu-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.13 \
    UV_PROJECT_ENVIRONMENT=/venv

ENV PATH="/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock /app/
RUN uv sync --no-install-project

COPY docker/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY docker/start-dev /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start


ENTRYPOINT ["/entrypoint"]
CMD ["/start"]


