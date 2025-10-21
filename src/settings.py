"""Module with the configuration parameters."""

import logging
from typing import Annotated
from functools import lru_cache
from enum import Enum
from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class LogLevelEnum(int, Enum):
    """Enumeration of supported logging levels."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def get_level(value: int | str | LogLevelEnum) -> int:
    """Convert a string, integer, or LogLevelEnum value to a logging level integer.

    Args:
        value: The log level as a string (case-insensitive), integer, or LogLevelEnum.

    Returns:
        int: The corresponding logging level integer.

    """
    if isinstance(value, str):
        return LogLevelEnum.__getitem__(value.upper())
    return value


class Settings(BaseSettings):
    """Model with the app settings."""
    KAFKA_ENABLE: Annotated[
        bool, Field(default=False, description="Enable kafka communication")
    ]
    KAFKA_BOOTSTRAP_SERVERS: Annotated[
        str,
        Field(
            default="localhost:9092",
            description="Kafka server hostnames. DNS name and port. Can be comma "
            "separeted list",
        ),
    ]
    KAFKA_TOPIC: Annotated[
        str,
        Field(
            default="federation-tests-result",
            description="Kafka topic with rally tests results",
        ),
    ]
    KAFKA_TOPIC_TIMEOUT: Annotated[
        int,
        Field(
            default=1000,
            ge=0,
            description="Number of ms to wait when reading published messages",
        ),
    ]
    KAFKA_MAX_REQUEST_SIZE: Annotated[
        int,
        Field(
            default=104857600,
            description="Maximum size of a request to send to kafka (B).",
        ),
    ]
    KAFKA_CLIENT_NAME: Annotated[
        str,
        Field(
            default="fedmgr-rally", description="Client name to use when connecting to kafka"
        ),
    ]
    KAFKA_SSL_ENABLE: Annotated[
        bool, Field(default=False, description="Enable SSL connection with kafka")
    ]
    KAFKA_SSL_CACERT_PATH: Annotated[
        str | None, Field(default=None, description="Path to the SSL CA cert file")
    ]
    KAFKA_SSL_CERT_PATH: Annotated[
        str | None, Field(default=None, description="Path to the SSL cert file")
    ]
    KAFKA_SSL_KEY_PATH: Annotated[
        str | None, Field(default=None, description="Path to the SSL Key file")
    ]
    KAFKA_SSL_PASSWORD: Annotated[
        str | None, Field(default=None, description="SSL password")
    ]
    KAFKA_ALLOW_AUTO_CREATE_TOPICS: Annotated[
        bool,
        Field(
            default=False,
            description="Enable automatic creation of new topics if not yet in kafka",
        ),
    ]
    KAFKA_MSG_VERSION: Annotated[
        str,
        Field(
            default="1.0.0",
            description="Message version for federation-tests-result topic. "
            "It defines the fields in the message sent to kafka",
        ),
    ]
    RALLY_ARGS_FOLDER: Annotated[
        str, Field(default="./data/", description="Folder for provider args"),
    ]
    RALLY_REPORT_FOLDER: Annotated[
        str, Field(default="./data/reports/", description="Folder for provider test results"),
    ]
    LOG_LEVEL: Annotated[
        LogLevelEnum,
        Field(default=LogLevelEnum.INFO, description="Logs level"),
        BeforeValidator(get_level),
    ]

    model_config = SettingsConfigDict(env_file=".env") 

@lru_cache
def get_settings() -> Settings:
    """Retrieve cached settings."""
    return Settings()
