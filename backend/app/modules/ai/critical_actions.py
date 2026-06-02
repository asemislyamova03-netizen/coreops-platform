from app.core.enums import AIActionType

CRITICAL_ACTION_TYPES: frozenset[AIActionType] = frozenset(
    {
        AIActionType.SEND_DOCUMENT,
        AIActionType.CREATE_INVOICE,
        AIActionType.UPDATE_PAYMENT,
        AIActionType.DELETE_DATA,
        AIActionType.SEND_MESSAGE,
        AIActionType.CHANGE_WORK_ITEM_STATUS,
        AIActionType.UPDATE_LEGAL_PROFILE,
    }
)


def is_critical_action(action_type: AIActionType) -> bool:
    return action_type in CRITICAL_ACTION_TYPES
