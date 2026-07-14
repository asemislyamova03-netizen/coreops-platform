from app.core.exceptions import ConflictError


class MarketingTopicNotApprovedError(ConflictError):
    def __init__(self) -> None:
        super().__init__("topic_not_approved")


class MarketingNoApprovedTopicsError(ConflictError):
    def __init__(self) -> None:
        super().__init__("no_approved_topics")


class MarketingTopicDuplicateBlockedError(ConflictError):
    def __init__(self, detail: str | None = None) -> None:
        message = "topic_duplicate_blocked"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)


class MarketingPackSlugExistsError(ConflictError):
    def __init__(self) -> None:
        super().__init__("pack_slug_exists")


class MarketingUnsupportedChannelError(ConflictError):
    def __init__(self, channel: str) -> None:
        super().__init__(f"unsupported_channel: {channel}")


class MarketingInvalidMimeTypeError(ConflictError):
    def __init__(self, mime_type: str) -> None:
        super().__init__(f"invalid_mime_type: {mime_type}")


class MarketingPreflightNotPassedError(ConflictError):
    def __init__(self) -> None:
        super().__init__("preflight_not_passed")


class MarketingInvalidPackStateError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
