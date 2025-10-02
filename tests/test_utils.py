from util import helpers
from datetime import datetime
import re

def test_format_datetime():
    dt = datetime(2025,1,1,13,45,59)
    assert helpers.format_datetime(dt) == "2025-01-01T13:45:59Z"

def test_generate_uuid():
    uuid_str = helpers.generate_uuid()
    assert re.match(r"^[0-9a-fA-F-]{36}$", uuid_str)
