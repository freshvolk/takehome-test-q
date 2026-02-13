FROM python:3.12-slim-trixie AS builder

RUN pip install poetry

WORKDIR /code

COPY pyproject.toml poetry.lock* /code/

RUN poetry config virtualenvs.in-project true
RUN poetry install --without dev --no-root

FROM python:3.12-slim-trixie AS final

RUN useradd --create-home quilteruser

WORKDIR /code

COPY --from=builder /code/.venv /code/.venv

COPY app /code/app

ARG BUILD_VERSION=unset
ENV APP_VERSION=$BUILD_VERSION

ENV PATH="/code/.venv/bin:$PATH"

USER quilteruser

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--port", "8000"]
