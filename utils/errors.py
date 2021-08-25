class ReportableError(Exception):
    """An error that should be reported to Discord in a message. Can be raised
    directly, or a more specific subclass can be raised. Subclassing
    `ReportableError` is done to make `try`/`except` statements more specific
    and does not affect how errors are reported in Discord.
    """

    log: bool

    def __init__(self, *args, log: bool = False):
        """If `log` is `False`, the error will not be logged, even if it is
        unhandled.
        """
        self.log = log
        super().__init__(*args)


class UserInputError(ReportableError):
    """An error relating to user input. Usually a more specific subclass
    should be raised instead of raising `UserInputError` directly.
    """


class UserTimeoutError(UserInputError):
    """An error relating to a user not responding to an input prompt fast
    enough.
    """


class UserCancelError(UserInputError):
    """An error relating to a user cancelling an input prompt."""


class ParseError(UserInputError):
    """An error relating to not being able to parse user input."""
