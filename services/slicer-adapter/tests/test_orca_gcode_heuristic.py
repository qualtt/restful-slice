"""Проверка эвристики «похоже на G-code» для ответа Orca."""

from src.clients.orca_client import _body_looks_like_gcode


def test_empty_not_gcode() -> None:
    assert _body_looks_like_gcode(b"") is False


def test_zip_magic_not_validated_here() -> None:
    # ZIP (PK) отсекается отдельно в slice_model; эвристика только про текст
    assert _body_looks_like_gcode(b"PK\x03\x04") is False


def test_typical_gcode_header() -> None:
    body = b"; FLAVOR:Marlin\nG90\nG21\nM104 S200"
    assert _body_looks_like_gcode(body) is True


def test_g_command_without_semicolon_first() -> None:
    assert _body_looks_like_gcode(b"\n\nG28 ; home\n") is True


def test_random_bytes() -> None:
    assert _body_looks_like_gcode(b"\x00\x01\x02\xff\xfe") is False
