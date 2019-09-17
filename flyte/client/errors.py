class FlyteClientError(Exception):
    """Base class for Client errors"""

    def __init__(self, msg, original_exception=None):
        if original_exception is not None:
            super(FlyteClientError, self).__init__(msg + (": %s" % original_exception))
        else:
            super(FlyteClientError, self).__init__(msg)
        self.original_exception = original_exception


class FlyteRequestError(FlyteClientError):
    """Error raised when there's a problem with the request that's being submitted.
    """

    def __init__(self, url, original_exception):
        super().__init__(f"failed when calling {url}", original_exception)
