import json
import logging

import pytest

from pipeline_demo_api.logging import JsonFormatter

pytestmark = pytest.mark.unit


def test_structured_logging_limits_fields() -> None:
    record = logging.LogRecord("test", logging.INFO, "test.py", 1, "http_request", (), None)
    record.status = 200
    record.authorization = "synthetic-secret"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "http_request"
    assert payload["status"] == 200
    assert "authorization" not in payload
