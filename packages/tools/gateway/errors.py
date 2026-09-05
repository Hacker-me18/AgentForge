"""Tool gateway error types."""


class ToolGatewayError(Exception):
    """Base class for tool gateway errors."""


class ToolNotFoundError(ToolGatewayError):
    """The requested tool is not registered."""


class PolicyDeniedError(ToolGatewayError):
    """The policy engine denied (or gated) the tool call."""


class ToolExecutionError(ToolGatewayError):
    """The tool itself failed (raised through to runtime retry logic)."""
