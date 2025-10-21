ARG PYTHON_VERSION=3.13
ARG POETRY_VERSION=2.1

FROM harbor.cloud.infn.it/datacloud-middleware/poetry:${POETRY_VERSION}-python${PYTHON_VERSION} AS base

WORKDIR /app

ENV RALLY_ENVS_FOLDER=/app/environments
ENV RALLY_ARGS_FOLDER=/app/args
ENV RALLY_REPORT_FOLDER=/app/reports

COPY ./pyproject.toml ./poetry.lock ./README.md /app/
COPY ./src /app/src
COPY ./rally-data /app/rally-data

RUN mkdir /app/environments
RUN mkdir /app/args
RUN mkdir /app/reports
RUN poetry install --no-root