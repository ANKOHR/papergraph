class PaperGraphError(Exception):
    """Base error for actionable PaperGraph failures."""


class PaperFormatError(PaperGraphError, ValueError):
    """A fixture paper is malformed or has unresolved references."""
