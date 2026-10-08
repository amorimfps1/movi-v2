from django.conf import settings
from rest_framework.exceptions import APIException


class DecisionRequired(APIException):
    status_code = 409
    default_code = "decision_required"

    def __init__(self, detail, decisions):
        super().__init__({"detail": detail, "decisions": decisions})


def approved(rule):
    return rule in getattr(settings, "BUSINESS_APPROVALS", [])
