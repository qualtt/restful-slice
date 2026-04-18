"""Тесты поведения RabbitMQ-клиента при публикации и обработке доставок."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from src.clients.rabbit_client import (
    RequeueMessageError,
    handle_consumer_message,
    publish_event_with_retries,
)


class _DummyEvent(BaseModel):
    x: int = 1


def test_publish_event_with_retries_raises_requeue_message_after_exhausted_attempts() -> None:
    with patch("src.clients.rabbit_client.publish_event") as mock_publish:
        mock_publish.side_effect = ConnectionError("broker down")
        with patch("src.clients.rabbit_client.time.sleep"):
            with pytest.raises(RequeueMessageError) as exc_info:
                publish_event_with_retries("slicing.results", _DummyEvent(), max_attempts=3)
        assert mock_publish.call_count == 3
        assert exc_info.value.__cause__ is not None


def test_handle_consumer_message_requeues_on_requeue_message_error() -> None:
    ch = MagicMock()
    method = MagicMock()
    method.delivery_tag = 42

    def _cb(_: str) -> None:
        raise RequeueMessageError("cannot publish")

    handle_consumer_message(ch, method, b"{}", _cb)
    ch.basic_reject.assert_called_once_with(delivery_tag=42, requeue=True)
    ch.basic_ack.assert_not_called()


def test_handle_consumer_message_rejects_without_requeue_on_generic_error() -> None:
    ch = MagicMock()
    method = MagicMock()
    method.delivery_tag = 7

    def _cb(_: str) -> None:
        raise RuntimeError("bad payload")

    handle_consumer_message(ch, method, b"{}", _cb)
    ch.basic_reject.assert_called_once_with(delivery_tag=7, requeue=False)
    ch.basic_ack.assert_not_called()


def test_handle_consumer_message_acks_on_success() -> None:
    ch = MagicMock()
    method = MagicMock()
    method.delivery_tag = 99

    def _cb(_: str) -> None:
        return None

    handle_consumer_message(ch, method, b"{}", _cb)
    ch.basic_ack.assert_called_once_with(delivery_tag=99)
    ch.basic_reject.assert_not_called()
