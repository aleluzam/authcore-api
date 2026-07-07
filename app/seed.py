from sqlalchemy import select
from app.models.users import RoleTable
from app.database import AsyncSessionLocal

DEFAULT_ROLES = ["user", "admin"]

async def ensure_default_roles():
    async with AsyncSessionLocal() as db:
        for rolename in DEFAULT_ROLES:
            result = await db.execute(
                select(RoleTable).where(RoleTable.rolename == rolename)
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                db.add(RoleTable(rolename=rolename))

        await db.commit()
