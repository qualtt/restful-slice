import json
from unittest.mock import MagicMock, patch

import pika
import pytest
from fastapi.responses import JSONResponse

from src.clients.rabbit_client import JOBS_QUEUE, check_broker_reachable
from src.main import health, health_check, health_live


def _fake_settings(amqp_url: str = "amqp://guest:guest@127.0.0.1:5672/") -> MagicMock:
    s = MagicMock()
    s.amqp_url = amqp_url
    return s


@patch("src.clients.rabbit_client.pika.BlockingConnection")
@patch("src.clients.rabbit_client.get_settings")
def test_check_broker_reachable_sets_socket_timeout_and_declares_queue(
    mock_get_settings: MagicMock,
    mock_blocking_connection: MagicMock,
) -> None:
    mock_get_settings.return_value = _fake_settings()
    mock_conn = MagicMock()
    mock_ch = MagicMock()
    mock_blocking_connection.return_value = mock_conn
    mock_conn.channel.return_value = mock_ch

    check_broker_reachable(timeout_seconds=3.5)

    mock_blocking_connection.assert_called_once()
    params = mock_blocking_connection.call_args[0][0]
    assert isinstance(params, pika.URLParameters)
    assert params.socket_timeout == 3.5
    mock_conn.channel.assert_called_once()
    mock_ch.queue_declare.assert_called_once_with(queue=JOBS_QUEUE, durable=True)
    mock_conn.close.assert_called_once()


@patch("src.clients.rabbit_client.pika.BlockingConnection")
@patch("src.clients.rabbit_client.get_settings")
def test_check_broker_reachable_closes_connection_when_queue_declare_fails(
    mock_get_settings: MagicMock,
    mock_blocking_connection: MagicMock,
) -> None:
    mock_get_settings.return_value = _fake_settings()
    mock_conn = MagicMock()
    mock_ch = MagicMock()
    mock_ch.queue_declare.side_effect = RuntimeError("queue_declare failed")
    mock_blocking_connection.return_value = mock_conn
    mock_conn.channel.return_value = mock_ch

    with pytest.raises(RuntimeError, match="queue_declare failed"):
        check_broker_reachable()

    mock_conn.close.assert_called_once()


@patch("src.clients.rabbit_client.pika.BlockingConnection")
@patch("src.clients.rabbit_client.get_settings")
def test_check_broker_reachable_propagates_connection_error(
    mock_get_settings: MagicMock,
    mock_blocking_connection: MagicMock,
) -> None:
    mock_get_settings.return_value = _fake_settings()
    mock_blocking_connection.side_effect = pika.exceptions.AMQPConnectionError("refused")

    with pytest.raises(pika.exceptions.AMQPConnectionError, match="refused"):
        check_broker_reachable()


@patch("src.clients.rabbit_client.pika.BlockingConnection")
@patch("src.clients.rabbit_client.get_settings")
def test_health_check_ok_when_broker_check_succeeds(
    mock_get_settings: MagicMock,
    mock_blocking_connection: MagicMock,
) -> None:
    mock_get_settings.return_value = _fake_settings()
    mock_conn = MagicMock()
    mock_ch = MagicMock()
    mock_blocking_connection.return_value = mock_conn
    mock_conn.channel.return_value = mock_ch

    with patch("src.main._check_minio", return_value="ok"), patch(
        "src.main._check_orca", return_value="ok"
    ), patch(
        "src.main.worker_thread",
        MagicMock(is_alive=MagicMock(return_value=True)),
    ), patch(
        "src.main.get_consumer_state",
        return_value={"last_success": "2025-01-01T00:00:00Z", "last_error": None},
    ):
        out = health_check()

    assert out == {
        "status": "healthy",
        "rabbitmq": "ok",
        "minio": "ok",
        "orca": "ok",
        "worker_thread_alive": True,
        "last_success": "2025-01-01T00:00:00Z",
        "last_error": None,
    }
    mock_ch.queue_declare.assert_called_once_with(queue=JOBS_QUEUE, durable=True)
    mock_conn.close.assert_called_once()


@patch("src.clients.rabbit_client.pika.BlockingConnection")
@patch("src.clients.rabbit_client.get_settings")
def test_health_check_503_when_broker_raises(
    mock_get_settings: MagicMock,
    mock_blocking_connection: MagicMock,
) -> None:
    mock_get_settings.return_value = _fake_settings()
    mock_blocking_connection.side_effect = ConnectionError("broker down")

    out = health_check()

    assert isinstance(out, JSONResponse)
    assert out.status_code == 503
    body = json.loads(out.body.decode())
    assert body["status"] == "unhealthy"
    assert body["error"] == "broker down"


def test_health_check_truncates_rabbitmq_error_to_500_chars() -> None:
    long_msg = "E" * 800
    with patch(
        "src.main.check_broker_reachable",
        side_effect=RuntimeError(long_msg),
    ):
        out = health_check()

    assert isinstance(out, JSONResponse)
    body = json.loads(out.body.decode())
    assert len(body["error"]) == 500
    assert body["error"] == long_msg[:500]


def test_health_live_reports_worker_thread_state() -> None:
    with patch(
        "src.main.worker_thread",
        MagicMock(is_alive=MagicMock(return_value=True)),
    ), patch(
        "src.main.get_consumer_state",
        return_value={"last_success": "2025-01-01T00:00:00Z", "last_error": None},
    ):
        out = health_live()

    assert out["status"] == "healthy"
    assert out["worker_thread_alive"] is True


def test_health_alias_matches_ready() -> None:
    with patch("src.clients.rabbit_client.get_settings", return_value=_fake_settings()), patch(
        "src.main.get_settings", return_value=MagicMock(minio_endpoint="minio:9000")
    ), patch(
        "src.main._check_minio", return_value="ok"
    ), patch(
        "src.main._check_orca", return_value="ok"
    ), patch(
        "src.main.worker_thread",
        MagicMock(is_alive=MagicMock(return_value=True)),
    ), patch(
        "src.main.get_consumer_state",
        return_value={"last_success": None, "last_error": None},
    ), patch("src.clients.rabbit_client.pika.BlockingConnection") as mock_conn:
        mock_conn.return_value.channel.return_value = MagicMock()
        response = health()

    assert response["status"] == "healthy"
