import logging
import time
import threading
from typing import Callable

import pika
from pydantic import BaseModel

from src.core.config import get_settings

logger = logging.getLogger(__name__)

JOBS_QUEUE = "slicing.jobs"
_consumer_state_lock = threading.Lock()
_consumer_state: dict[str, str | None] = {"last_success": None, "last_error": None}


class RequeueMessageError(Exception):
    """Raised when the job must be redelivered (e.g. could not publish to the results queue)."""


def record_consumer_success() -> None:
    with _consumer_state_lock:
        _consumer_state["last_success"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _consumer_state["last_error"] = None


def record_consumer_error(error: str) -> None:
    with _consumer_state_lock:
        _consumer_state["last_error"] = error[:500]


def get_consumer_state() -> dict[str, str | None]:
    with _consumer_state_lock:
        return dict(_consumer_state)


def handle_consumer_message(
    ch: pika.channel.Channel,
    method: pika.spec.Basic.Deliver,
    body: bytes,
    callback: Callable[[str], None],
) -> None:
    try:
        callback(body.decode("utf-8"))
        record_consumer_success()
    except RequeueMessageError:
        logger.warning(
            "Requeueing message: downstream publish unavailable or exhausted retries",
            exc_info=True,
        )
        record_consumer_error("downstream publish unavailable")
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
        return
    except Exception:
        logger.exception(
            "Fatal error while handling message; rejecting without requeue"
        )
        record_consumer_error("fatal consumer error")
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        return
    ch.basic_ack(delivery_tag=method.delivery_tag)


def check_broker_reachable(timeout_seconds: float = 2.0) -> None:
    """Быстрая проверка AMQP: подключение и очередь slicing.jobs (как у consumer)."""
    settings = get_settings()
    params = pika.URLParameters(settings.amqp_url)
    params.socket_timeout = timeout_seconds
    connection: pika.BlockingConnection | None = None
    try:
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=JOBS_QUEUE, durable=True)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                logger.debug(
                    "Failed to close RabbitMQ connection after healthcheck",
                    exc_info=True,
                )


def publish_event(queue_name: str, event: BaseModel) -> None:
    settings = get_settings()
    body = event.model_dump_json().encode("utf-8")
    connection: pika.BlockingConnection | None = None
    try:
        params = pika.URLParameters(settings.amqp_url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                logger.debug(
                    "Failed to close RabbitMQ connection after publish", exc_info=True
                )


def publish_event_with_retries(
    queue_name: str,
    event: BaseModel,
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 0.5,
) -> None:
    """Publish with retries; on total failure raises RequeueMessageError for the job consumer."""
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            publish_event(queue_name, event)
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Publish attempt %s/%s failed for queue=%s: %s",
                attempt,
                max_attempts,
                queue_name,
                exc,
            )
            if attempt < max_attempts:
                time.sleep(backoff_seconds * attempt)
    raise RequeueMessageError(
        f"Failed to publish to {queue_name} after {max_attempts} attempts"
    ) from last_exc


def start_consuming(queue_name: str, callback: Callable[[str], None]) -> None:
    settings = get_settings()
    while True:
        connection: pika.BlockingConnection | None = None
        try:
            params = pika.URLParameters(settings.amqp_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)

            def _on_message(
                ch: pika.channel.Channel,
                method: pika.spec.Basic.Deliver,
                _properties: pika.spec.BasicProperties,
                body: bytes,
            ) -> None:
                handle_consumer_message(ch, method, body, callback)

            channel.basic_consume(
                queue=queue_name, on_message_callback=_on_message, auto_ack=False
            )
            logger.info("Consuming queue %s", queue_name)
            channel.start_consuming()
        except Exception:
            logger.exception(
                "RabbitMQ consumer crashed for queue %s, retrying in 5s",
                queue_name,
            )
            record_consumer_error(f"consumer crashed for queue {queue_name}")
            time.sleep(5)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    logger.debug(
                        "Failed to close RabbitMQ connection after consumer loop",
                        exc_info=True,
                    )
