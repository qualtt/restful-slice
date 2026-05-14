import json
import logging
import threading
import time
from typing import Callable
from uuid import uuid4
from datetime import datetime, timezone

import pika

from core.config import get_settings

logger = logging.getLogger(__name__)

JOBS_QUEUE = "slicing.jobs"
RESULTS_QUEUE = "slicing.results"


def publish_slice_requested(
    order_id: str,
    file_object_key: str,
    profile_id: int,
) -> None:
    settings = get_settings()
    event = {
        "event_id": str(uuid4()),
        "event_type": "slice.requested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "order-service",
        "spec_version": "1.0.0",
        "payload": {
            "order_id": order_id,
            "customer_id": "00000000-0000-0000-0000-000000000000",
            "priority": "normal",
            "minio_paths": {
                "stl_file": file_object_key,
                "printer_profile": f"profiles/{profile_id}/printer.json",
                "process_profile": f"profiles/{profile_id}/process.json",
                "filament_profile": f"profiles/{profile_id}/filament.json",
            },
        },
    }
    body = json.dumps(event).encode("utf-8")
    params = pika.URLParameters(settings.amqp_url)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=JOBS_QUEUE, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=JOBS_QUEUE,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    finally:
        try:
            connection.close()
        except Exception:
            pass


def start_results_consumer(callback: Callable[[str], None]) -> None:
    def _run():
        settings = get_settings()
        while True:
            try:
                params = pika.URLParameters(settings.amqp_url)
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.queue_declare(queue=RESULTS_QUEUE, durable=True)
                channel.basic_qos(prefetch_count=1)

                def _on_message(ch, method, _props, body):
                    try:
                        callback(body.decode("utf-8"))
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception:
                        logger.exception("Error processing slicing result")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                channel.basic_consume(
                    queue=RESULTS_QUEUE,
                    on_message_callback=_on_message,
                    auto_ack=False,
                )
                logger.info("Consuming slicing.results queue")
                channel.start_consuming()
            except Exception:
                logger.exception("RabbitMQ consumer error, retrying in 5s")
                time.sleep(5)

    t = threading.Thread(target=_run, daemon=True, name="results-consumer")
    t.start()
