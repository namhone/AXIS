import uuid

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.core.database import Base, _enable_sqlite_foreign_keys
from app.models.profile import Profile
from app.models.user import User


def test_sqlite_foreign_keys_enforce_profile_cascade() -> None:
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            user = User(
                id=uuid.uuid4(),
                email="cascade@example.com",
                full_name="Cascade Test",
                password_hash="unused",
            )
            db.add(user)
            db.flush()
            db.add(Profile(user_id=user.id, data={}, subject=None))
            db.commit()

            db.delete(user)
            db.commit()

            assert db.scalar(select(func.count()).select_from(Profile)) == 0
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
