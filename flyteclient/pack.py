from dataclasses import dataclass
from typing import List

from dataclasses_json import dataclass_json, LetterCase

from flyteclient.definitions import EventDef


@dataclass
@dataclass_json(letter_case=LetterCase.CAMEL)
class Link(object):
    href: str
    rel: str


@dataclass
@dataclass_json
class Action:
    command: str
    input: str
    links: List[Link]

    def __init__(self, command: str, input: str, links: List[Link] = []) -> None:
        self.links = links
        self.input = input
        self.command = command

    def get_action_complete_url(self):
        """returns action complete url if found"""
        return next(link.href for link in self.links if link.rel.endswith("actionResult"))


@dataclass
@dataclass_json(letter_case=LetterCase.CAMEL)
class Event(object):
    event: str
    payload: str

    def __init__(self, event: str, payload: str = None) -> None:
        self.payload = payload
        self.event = event


@dataclass
@dataclass_json(letter_case=LetterCase.CAMEL)
class Command(object):
    name: str
    events: List[str]

    def __init__(self, name: str, events: List[str] = None) -> None:
        self.events = events
        self.name = name


@dataclass
@dataclass_json(letter_case=LetterCase.CAMEL)
class Pack(object):
    name: str
    links: List[Link]
    commands: List[Command]
    events: List[EventDef]

    def __init__(self, name: str = None,
                 links: List[Link] = [],
                 commands: List[Command] = [],
                 events: List[EventDef] = []) -> None:
        self.events = events
        self.commands = commands
        self.links = links
        self.name = name

    def get_take_action_url(self):
        """returns take action url if found"""
        return next(link.href for link in self.links if link.rel.endswith("takeAction"))

    def get_events_url(self):
        """returns post event url if found"""
        return next(link.href for link in self.links if link.rel.endswith("event"))

