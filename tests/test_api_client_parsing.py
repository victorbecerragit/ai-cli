"""Tests for the JSON and SSE extraction logic in api_client.

These are *pure unit tests* – no HTTP calls, no network, no browser.
We import the private helpers directly and supply carefully crafted inputs.
"""

import json
from unittest.mock import MagicMock

from ai_cli.api_client import (
    COMMON_JSON_TEXT_FIELDS,
    _consume_sse,
    _extract_text,
)

# ---------------------------------------------------------------------------
# _extract_text – JSON paths
# ---------------------------------------------------------------------------


class TestExtractTextJson:
    """_extract_text resolves dotted paths into JSON responses."""

    def test_openai_choices_message_content(self) -> None:
        payload = json.dumps({"choices": [{"message": {"content": "Hello from OpenAI!"}}]})
        result = _extract_text(payload, "application/json", [])
        assert result == "Hello from OpenAI!"

    def test_openai_delta_content(self) -> None:
        payload = json.dumps({"choices": [{"delta": {"content": "streaming chunk"}}]})
        result = _extract_text(payload, "application/json", [])
        assert result == "streaming chunk"

    def test_simple_answer_field(self) -> None:
        payload = json.dumps({"answer": "42"})
        result = _extract_text(payload, "application/json", [])
        assert result == "42"

    def test_simple_text_field(self) -> None:
        payload = json.dumps({"text": "plain answer"})
        result = _extract_text(payload, "application/json", [])
        assert result == "plain answer"

    def test_response_field(self) -> None:
        payload = json.dumps({"response": "I am a bot"})
        result = _extract_text(payload, "application/json", [])
        assert result == "I am a bot"

    def test_custom_response_path_wins_over_common(self) -> None:
        payload = json.dumps({"custom": "override", "text": "fallback"})
        result = _extract_text(payload, "application/json", ["custom"])
        assert result == "override"

    def test_unknown_json_structure_returns_raw(self) -> None:
        payload = json.dumps({"totally": {"unknown": {"structure": True}}})
        result = _extract_text(payload, "application/json", [])
        # Should return a (possibly truncated) version of the raw input
        assert "totally" in result or result == "<empty response>"

    def test_json_autodetected_without_content_type(self) -> None:
        """A JSON body is recognised even with an empty content-type header."""
        payload = json.dumps({"message": "auto detected"})
        result = _extract_text(payload, "", [])
        assert result == "auto detected"

    def test_empty_json_object(self) -> None:
        result = _extract_text("{}", "application/json", [])
        # No extractable text path → falls back to raw or <empty response>
        assert isinstance(result, str) and result  # must be a non-empty string

    def test_json_array_falls_back_to_raw(self) -> None:
        payload = json.dumps([1, 2, 3])
        result = _extract_text(payload, "application/json", [])
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _extract_text – SSE content-type
# ---------------------------------------------------------------------------


class TestExtractTextSse:
    """_extract_text handles text/event-stream (non-streaming fallback path)."""

    def test_sse_plain_data_lines(self) -> None:
        raw = "data: hello\ndata: world\ndata: [DONE]\n"
        result = _extract_text(raw, "text/event-stream", [])
        assert result == "helloworld"

    def test_sse_json_events_extract_content(self) -> None:
        raw = 'data: {"content": "Hi "}\ndata: {"content": "there"}\ndata: [DONE]\n'
        result = _extract_text(raw, "text/event-stream", [])
        assert result == "Hi there"

    def test_sse_empty_stream_returns_placeholder(self) -> None:
        raw = "data: [DONE]\n"
        result = _extract_text(raw, "text/event-stream", [])
        assert result == "<empty response>"

    def test_sse_no_data_lines_returns_placeholder(self) -> None:
        raw = "event: ping\n: keep-alive\n"
        result = _extract_text(raw, "text/event-stream", [])
        assert result == "<empty response>"


# ---------------------------------------------------------------------------
# _extract_text – plain text
# ---------------------------------------------------------------------------


class TestExtractTextPlain:
    def test_plain_text_returned_as_is(self) -> None:
        result = _extract_text("just some text", "text/plain", [])
        assert result == "just some text"

    def test_empty_plain_text_returns_placeholder(self) -> None:
        result = _extract_text("   ", "text/plain", [])
        assert result == "<empty response>"

    def test_html_content_type_returned_as_is(self) -> None:
        result = _extract_text("<p>hello</p>", "text/html", [])
        assert result == "<p>hello</p>"


# ---------------------------------------------------------------------------
# _consume_sse – live streaming via mocked Response
# ---------------------------------------------------------------------------


class TestConsumeSse:
    """_consume_sse iterates over a mocked requests.Response."""

    def _make_response(self, lines: list[str]) -> MagicMock:
        response = MagicMock()
        response.iter_lines.return_value = iter(lines)
        return response

    def test_plain_data_chunks_joined(self) -> None:
        response = self._make_response(["data: foo", "data: bar", "data: [DONE]"])
        text, raw = _consume_sse(response, ["content"])
        assert text == "foobar"
        assert raw is not None

    def test_json_event_content_extracted(self) -> None:
        response = self._make_response(
            [
                'data: {"content": "Hello "}',
                'data: {"content": "world"}',
                "data: [DONE]",
            ]
        )
        text, _ = _consume_sse(response, ["content"])
        assert text == "Hello world"

    def test_done_stops_iteration(self) -> None:
        response = self._make_response(["data: before", "data: [DONE]", "data: after"])
        text, _ = _consume_sse(response, ["content"])
        assert "before" in text
        assert "after" not in text

    def test_empty_lines_are_skipped(self) -> None:
        response = self._make_response(["", "data: content", "", "data: [DONE]"])
        text, _ = _consume_sse(response, ["content"])
        assert text == "content"

    def test_non_data_lines_are_ignored(self) -> None:
        response = self._make_response(["event: ping", ": comment", "data: real", "data: [DONE]"])
        text, _ = _consume_sse(response, ["content"])
        assert text == "real"

    def test_empty_stream_returns_placeholder(self) -> None:
        response = self._make_response(["data: [DONE]"])
        text, _ = _consume_sse(response, ["content"])
        assert text == "<empty response>"

    def test_raw_preview_is_returned(self) -> None:
        response = self._make_response(["data: hello", "data: [DONE]"])
        _, raw = _consume_sse(response, ["content"])
        assert raw is not None
        assert "data: hello" in raw


# ---------------------------------------------------------------------------
# COMMON_JSON_TEXT_FIELDS sanity check
# ---------------------------------------------------------------------------


def test_common_json_fields_contains_expected_paths() -> None:
    """Ensure well-known field names are present for compatibility."""
    for field in ("text", "response", "answer", "content", "message"):
        assert field in COMMON_JSON_TEXT_FIELDS

    # OpenAI-style dotted paths must be present
    assert "choices.0.message.content" in COMMON_JSON_TEXT_FIELDS
    assert "choices.0.delta.content" in COMMON_JSON_TEXT_FIELDS
