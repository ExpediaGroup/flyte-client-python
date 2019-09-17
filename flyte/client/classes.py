from dataclasses import dataclass, field
from typing import List, Dict

from dataclasses_json import dataclass_json


@dataclass
@dataclass_json
class Link(object):
    """
    link to navigate through our api using hateoas
    """

    href: str
    rel: str


@dataclass
@dataclass_json
class Action:
    """
    represents a command to be executed
    """

    command: str
    input: str
    links: List[Link] = field(default_factory=list)

    def get_action_complete_url(self):
        """returns action complete url if found
        :raises ValueError if link not found
        """
        return find_url_by_relative_name(self.links, "actionResult")


@dataclass
@dataclass_json
class Event:
    """
    represents an input/output event
    """

    event: str
    payload: str = None


@dataclass
@dataclass_json
class Command:
    """
    represents the commands a pack exposes
    """

    name: str
    events: List[str] = field(default_factory=list)
    links: List[Link] = field(default_factory=list)


@dataclass
@dataclass_json
class EventDef:
    """
    the event definition, this describes events a pack can send
    """

    name: str
    links: [Link] = field(default_factory=list)


@dataclass
@dataclass_json
class Pack:
    name: str
    labels: Dict[str, str] = field(default_factory=lambda: {})
    links: List[Link] = field(default_factory=list)
    commands: List[Command] = field(default_factory=list)
    events: List[EventDef] = field(default_factory=list)

    def get_take_action_url(self):
        """returns take action url if found
        :raises ValueError if link not found"""
        return find_url_by_relative_name(self.links, "takeAction")

    def get_events_url(self):
        """returns post event url if found
        :raises ValueError if link not found"""
        return find_url_by_relative_name(self.links, "event")


def find_url_by_relative_name(links: List[Link], rel_name: str) -> str:
    """
    finds a url inside a list of links using its relative name
    :param links: list of links
    :param rel_name: relative name
    :return: url
    """
    link = next((link.href for link in links if link.rel.endswith(rel_name)), None)
    if link is None:
        raise ValueError(f"link {rel_name} not found")
    return link
