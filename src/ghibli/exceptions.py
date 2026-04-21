class GhibliError(Exception):
    pass


class ToolCallError(GhibliError):
    pass


class GitHubAPIError(GhibliError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class SessionError(GhibliError):
    pass


class OutputError(GhibliError):
    pass
