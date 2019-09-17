import unittest
from unittest import TestCase

from flyte.pack.classes import Command, CommandHandler, EventDef, PackDef, Event
from flyte.pack.mappers import to_event_list_name, to_client_command, to_client_event_def, to_client_pack, \
    to_client_event
from flyte.client.classes import Command as ClientCommand, Link, EventDef as ClientEventDef, Pack as ClientPack, \
    Event as ClientEvent


class TestMappers(TestCase):

    def test_to_client_event(self):
        event = Event(eventDef=EventDef(name="event1", help_url="http://url.com"), payload="payload")
        self.assertEqual(ClientEvent(event="event1", payload="payload"), to_client_event(event))

    def test_convert_commands_to_client_commands(self):
        command = Command(
            name="command1",
            handler=CommandHandler(),
            output_events=[
                EventDef(name="event1", help_url="help1"),
                EventDef(name="event2", help_url="help2"),
                EventDef(name="event3", help_url="help3"),
            ],
            help_url="http://help.hcom/command1"
        )
        client_command = ClientCommand(
            name="command1",
            events=["event1", "event2", "event3"],
            links=[Link(href="http://help.hcom/command1", rel="help")],
        )
        self.assertEqual(client_command, to_client_command(command))

    def test_convert_events_def_to_list_of_names(self):
        self.assertEqual(["event1", "event2", "event3"], to_event_list_name([
            EventDef(name="event1", help_url="help1"),
            EventDef(name="event2", help_url="help2"),
            EventDef(name="event3", help_url="help3"),
        ]))

    def test_convert_event_def_to_client_event_def(self):
        self.assertEqual(ClientEventDef(name="event-def-1", links=[
            Link(href="http://help.hcom/event1", rel="help")
        ]), to_client_event_def(EventDef(name="event-def-1", help_url="http://help.hcom/event1")))

    def test_convert_packdef_to_client_pack(self):
        cp = ClientPack(
            name="name",
            labels={"label": "value"},
            links=[Link(href="http://help.hcom/pack", rel="help")],
            events=[
                ClientEventDef(name="spontaneous", links=[
                    Link(href="http://help.hcom/spontaneous", rel="help"),
                ]),
                ClientEventDef(name="output1-command1", links=[
                    Link(href="http://help.hcom/output1-command1", rel="help"),
                ]),
                ClientEventDef(name="output2-command1", links=[
                    Link(href="http://help.hcom/output2-command1", rel="help"),
                ]),
                ClientEventDef(name="output3-command1", links=[
                    Link(href="http://help.hcom/output3-command1", rel="help"),
                ]), ClientEventDef(name="output1-command2", links=[
                    Link(href="http://help.hcom/output1-command2", rel="help"),
                ]),
                ClientEventDef(name="output2-command2", links=[
                    Link(href="http://help.hcom/output2-command2", rel="help"),
                ]),
                ClientEventDef(name="output3-command2", links=[
                    Link(href="http://help.hcom/output3-command2", rel="help"),
                ])
            ],
            commands=[
                ClientCommand(name="command1",
                              events=["output1-command1", "output2-command1", "output3-command1"],
                              links=[
                                  Link(href="http://help.hcom/command1", rel="help")
                              ]),
                ClientCommand(name="command2",
                              events=["output1-command2", "output2-command2", "output3-command2"],
                              links=[
                                  Link(href="http://help.hcom/command2", rel="help")
                              ])
            ],
        )
        pd = PackDef(
            name="name",
            labels={"label": "value"},
            help_url="http://help.hcom/pack",
            event_defs=[EventDef(name="spontaneous", help_url="http://help.hcom/spontaneous")],
            commands=[
                Command(name="command1",
                        help_url="http://help.hcom/command1",
                        output_events=[
                            EventDef(name="output1-command1", help_url="http://help.hcom/output1-command1"),
                            EventDef(name="output2-command1", help_url="http://help.hcom/output2-command1"),
                            EventDef(name="output3-command1", help_url="http://help.hcom/output3-command1"),
                        ],
                        handler=CommandHandler()),
                Command(name="command2",
                        help_url="http://help.hcom/command2",
                        output_events=[
                            EventDef(name="output1-command2", help_url="http://help.hcom/output1-command2"),
                            EventDef(name="output2-command2", help_url="http://help.hcom/output2-command2"),
                            EventDef(name="output3-command2", help_url="http://help.hcom/output3-command2"),
                        ],
                        handler=CommandHandler())
            ],
        )
        self.assertEqual(cp, to_client_pack(pd))


if __name__ == '__main__':
    unittest.main()
