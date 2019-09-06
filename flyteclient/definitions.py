from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import dataclass_json, LetterCase


class CommandHandler(ABC):
    """
    The Handler interface declares a method for building the chain of handlers.
    It also declares a method for executing a request.
    """

    @abstractmethod
    def handle(self, request) -> ABC:
        pass


@dataclass
@dataclass_json(letter_case=LetterCase.CAMEL)
class EventDef:
    name: str
    help_url: Optional['str'] = None


@dataclass
class CommandDef(object):
    def __init__(self, name: str, handler: CommandHandler, help_url: str = "",
                 output_events: List[EventDef] = None) -> None:
        self.output_events = output_events
        self.help_url = help_url
        self.handler = handler
        self.name = name


@dataclass
class PackDef(object):
    def __init__(self, name: str, commands: List[CommandDef], help_url: str) -> None:
        self.name = name
        self.help_url = help_url
        self.commands = commands
