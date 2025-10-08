import json
from logging import Logger
from typing import Any

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from settings import Settings


def add_ssl_parameters(
    settings: Settings,
) -> dict[str, Any]:
    """Add SSL configuration parameters for Kafka connection based on provided settings.

    This function reads the SSL password from a file specified in the settings and
    constructs a dictionary of SSL-related keyword arguments required for secure Kafka
    communication.

    Args:
        settings (Settings): The settings object containing
            Kafka SSL configuration paths.

    Returns:
        dict[str, Any]: A dictionary containing SSL configuration parameters for Kafka.

    """
    kwargs = {
        "security_protocol": "SSL",
        "ssl_check_hostname": False,
        "ssl_cafile": settings.KAFKA_SSL_CACERT_PATH,
        "ssl_certfile": settings.KAFKA_SSL_CERT_PATH,
        "ssl_keyfile": settings.KAFKA_SSL_KEY_PATH,
        "ssl_password": settings.KAFKA_SSL_PASSWORD,
    }
    return kwargs



def create_kafka_producer(
    *, settings: Settings
) -> KafkaProducer:
    """Create and configure a KafkaProducer instance based on the provided settings.

    This function sets up a Kafka producer with JSON value serialization, idempotence,
    and other options as specified in the `settings` object. If SSL is enabled, it loads
    the necessary SSL certificates and password from the provided paths.

    Args:
        settings (Settings): Configuration object containing Kafka connection
            and security settings.

    Returns:
        KafkaProducer: Configured Kafka producer instance.

    Raises:
        ConfigurationError: If the Kafka broker is unavailable, required files are
            missing, or configuration is invalid.

    """
    kwargs = {
        "client_id": settings.KAFKA_CLIENT_NAME,
        "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "value_serializer": lambda x: json.dumps(x, sort_keys=True).encode("utf-8"),
        "max_request_size": settings.KAFKA_MAX_REQUEST_SIZE,
        "acks": "all",
        "enable_idempotence": True,
        "allow_auto_create_topics": settings.KAFKA_ALLOW_AUTO_CREATE_TOPICS,
    }

    try:
        if settings.KAFKA_SSL_ENABLE:
            print("SSL enabled")
            ssl_kwargs = add_ssl_parameters(settings=settings)
            kwargs = {**kwargs, **ssl_kwargs}

        return KafkaProducer(**kwargs)

    except NoBrokersAvailable as e:
        msg = f"Kakfa Broker not found at given url: {settings.KAFKA_BOOTSTRAP_SERVERS}"
        raise ConfigurationError(msg) from e
    except ValueError as e:
        msg = e.args[0]
        raise ConfigurationError(msg) from e
