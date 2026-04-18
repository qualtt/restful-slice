import logging
from typing import Callable

import pika
from pydantic import BaseModel

from src.core.config import get_settings

logger = logging.getLogger(__name__)


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


def start_consuming(queue_name: str, callback: Callable[[str], None]) -> None:
    settings = get_settings()
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
        try:
            callback(body.decode("utf-8"))
        except Exception:
            logger.exception(
                "Fatal error while handling message; rejecting without requeue"
            )
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=queue_name, on_message_callback=_on_message, auto_ack=False
    )
    logger.info("Consuming queue %s", queue_name)
    channel.start_consuming()
