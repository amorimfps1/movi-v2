from .models import AuditEvent


def record(actor, action, target, reason="", metadata=None):
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target_type=target._meta.label_lower,
        target_id=str(target.pk),
        reason=reason,
        metadata=metadata or {},
    )
