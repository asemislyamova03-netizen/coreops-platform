from app.core.exceptions import ConflictError, NotFoundError


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


class MarketingPublishingConnectionValidationError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingPublishingConnectionDuplicateError(ConflictError):
    def __init__(self) -> None:
        super().__init__("publishing_connection_duplicate")


class MarketingPublishingConnectionNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("publishing_connection_not_found")


class MarketingPublishingSecretLifecycleError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingStorageProfileValidationError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingStorageProfileNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("storage_profile_not_found")


class MarketingStorageProfileDuplicateActiveError(ConflictError):
    def __init__(self) -> None:
        super().__init__("storage_profile_active_duplicate")


class MarketingManagedMediaLifecycleError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingPublicUrlValidationError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingPublishDestinationValidationError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingPublishDestinationNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("publish_destination_not_found")


class MarketingPublishDestinationHardDeleteForbiddenError(ConflictError):
    def __init__(self) -> None:
        super().__init__("publish_destination_hard_delete_forbidden")


class MarketingGuideNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("marketing_guide_not_found")


class MarketingGuideValidationError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingRubricNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("marketing_rubric_not_found")


class MarketingRubricValidationError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingRubricDuplicateError(ConflictError):
    def __init__(self) -> None:
        super().__init__("marketing_rubric_duplicate")


class MarketingRubricNotSelectableError(ConflictError):
    """Inactive/archived rubric must not be chosen for a new consumable topic."""

    def __init__(self) -> None:
        super().__init__("marketing_rubric_not_selectable")


class MarketingRubricHardDeleteForbiddenError(ConflictError):
    def __init__(self) -> None:
        super().__init__("marketing_rubric_hard_delete_forbidden")


class MarketingContentPlanNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("marketing_content_plan_not_found")


class MarketingContentPlanItemNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("marketing_content_plan_item_not_found")


class MarketingContentPlanValidationError(ConflictError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class MarketingContentPlanImmutableError(ConflictError):
    def __init__(self, detail: str = "marketing_content_plan_immutable") -> None:
        super().__init__(detail)


class MarketingContentPlanItemDuplicateLineKeyError(ConflictError):
    def __init__(self) -> None:
        super().__init__("marketing_content_plan_item_line_key_duplicate")


class MarketingContentPlanHardDeleteForbiddenError(ConflictError):
    def __init__(self) -> None:
        super().__init__("marketing_content_plan_hard_delete_forbidden")
