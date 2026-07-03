from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_action(
    session: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: str | None = None,
    actor: str = "SYSTEM",
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        actor=actor,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.commit()
    return entry
