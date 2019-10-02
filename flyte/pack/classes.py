from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventDef:
    name: str
    help_url: str = ""


@dataclass
class Event:
    eventDef: EventDef
    payload: Any


class CommandHandler:
    """
    The Handler interface declares a method for building the chain of handlers.
    It also declares a method for executing a request.
    """

    @abstractmethod
    def handle(self, request) -> Event:
        pass


@dataclass
class Command:
    name: str
    handler: CommandHandler
    output_events: [EventDef] = field(default_factory=list)
    help_url: str = ""


@dataclass
class PackDef:
    name: str
    labels: {}
    event_defs: [EventDef]
    commands: [Command]
    help_url: str


def fatal_event(payload: Any) -> Event:
    return Event(eventDef=EventDef(name="FATAL"), payload=payload)
