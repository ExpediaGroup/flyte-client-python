from typing import Any

from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
class Health(object):
    healthy: bool
    status: Any


class HealthCheck(object):
    def start(self):
        None
