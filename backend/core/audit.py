from .models import AuditEvent


def record(actor, action, target, reason="", metadata=None):
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        # Stable audit identity: pre-migration events remain in the same history.
        target_type="core.student" if target._meta.label_lower == "core.person" else target._meta.label_lower,
        target_id=str(target.pk),
        reason=reason,
        metadata=metadata or {},
    )
