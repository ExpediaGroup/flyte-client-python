class PackError(Exception):
    """Base class for pack errors"""

    def __init__(self, msg, original_exception):
        super(PackError, self).__init__(msg + (": %s" % original_exception))
        self.original_exception = original_exception


class SendEventError(PackError):
    """
    Error raised when send event fails
    """

    def __init__(self, event, original_exception):
        super().__init__("Failed when sending event %s" % event, original_exception)
