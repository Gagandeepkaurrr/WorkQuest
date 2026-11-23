import asyncio
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.core.security import canonical_hash, now
from app.db import models  # noqa: F401
from app.db.sessions import Session
from app.engine.registry import CONTENT, load_scenario
from app.modules.scenarios.models import ScenarioRecord, ScenarioVersion


async def seed():
    async with Session.begin() as db:
        for path in sorted(CONTENT.glob("*/scenario.json")):
            definition = load_scenario(path.parent.name)
            data = definition.model_dump()
            hashed = canonical_hash(data)
            scenario = await db.scalar(
                select(ScenarioRecord)
                .where(ScenarioRecord.slug == definition.slug)
                .with_for_update()
            )
            if scenario:
                version = await db.get(
                    ScenarioVersion,
                    uuid5(
                        NAMESPACE_URL, f"workquest:{definition.slug}:v{definition.content_version}"
                    ),
                )
                if version and version.content_hash != hashed:
                    raise ValueError(
                        f"Published {definition.slug} differs. Create and publish an explicit new version."
                    )
                continue
            scenario = ScenarioRecord(
                id=uuid5(NAMESPACE_URL, f"workquest:{definition.slug}"),
                slug=definition.slug,
                public_metadata=definition.metadata.model_dump(),
            )
            db.add(scenario)
            await db.flush()
            version = ScenarioVersion(
                id=uuid5(
                    NAMESPACE_URL, f"workquest:{definition.slug}:v{definition.content_version}"
                ),
                scenario_id=scenario.id,
                version_number=definition.content_version,
                status="published",
                mechanics_id=definition.mechanics_id,
                definition_private_json=data,
                content_hash=hashed,
                validated_hash=hashed,
                published_at=now(),
            )
            db.add(version)
            await db.flush()
            scenario.active_published_version_id = version.id


if __name__ == "__main__":
    asyncio.run(seed())
    print("Authored scenarios seeded without default accounts.")
