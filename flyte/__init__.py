import logging
from logging import NullHandler

from flyte.client.client import Client  # noqa
from flyte.pack.pack import Pack  # noqa

# Set default logging handler to avoid "No handler found" warnings.
logging.getLogger(__name__).addHandler(NullHandler())
