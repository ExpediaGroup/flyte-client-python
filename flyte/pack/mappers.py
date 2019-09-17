from flyte.client.classes import (
    Command as ClientCommand,
    Link,
    EventDef as ClientEventDef,
    Pack as ClientPack,
    Event as ClientEvent,
)
from flyte.pack.classes import Command, EventDef, PackDef, Event


def to_client_command(from_obj: Command) -> ClientCommand:
    """converts a command to a flyte-client command
    :param from_obj command
    :return flyte-client command"""
    return ClientCommand(
        name=from_obj.name,
        events=to_event_list_name(from_obj.output_events),
        links=help_link(from_obj.help_url),
    )


def help_link(help_url: str) -> [Link]:
    """converts a string to a HATEOAS help link
    :param help_url url
    :return HATEOAS link"""
    return [Link(href=help_url, rel="help")] if help_url != "" else []


def to_event_list_name(from_obj: [EventDef]) -> [str]:
    """flats a list of events and returns only their event names
    :param from_obj list of events
    :return list of event names"""
    return list(map(lambda e: e.name, from_obj))


def to_client_event_def(from_obj: EventDef) -> ClientEventDef:
    """
    converts an event definition to a flyte-client event definition
    :param from_obj:
    :return: event definition for flyte-client
    """
    return ClientEventDef(name=from_obj.name, links=help_link(from_obj.help_url))


def to_client_pack(from_obj: PackDef) -> ClientPack:
    """converts a PackDef object to a flyte-client Pack
    :param from_obj pack definition
    :return a flyte-client pack instance"""
    command_events = []
    for command in from_obj.commands:
        for val in command.output_events:
            command_events.append(val)

    spontaneous_events = list(
        map(lambda e: to_client_event_def(e), from_obj.event_defs)
    )
    other = list(map(lambda e: to_client_event_def(e), command_events))
    return ClientPack(
        name=from_obj.name,
        labels=from_obj.labels,
        links=help_link(from_obj.help_url),
        events=spontaneous_events + other,
        commands=list(map(lambda c: to_client_command(c), from_obj.commands)),
    )


def to_client_event(from_obj: Event) -> ClientEvent:
    """converts pack events to client events
    :param from_obj Pack event
    :return client event
    """
    return ClientEvent(event=from_obj.eventDef.name, payload=from_obj.payload)
