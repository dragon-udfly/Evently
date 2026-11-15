import os

# must be set before the app is imported
os.environ["DATABASE_URL"] = "sqlite:///./test_eventsphere.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENABLE_SCHEDULER"] = "0"
os.environ["AGENT_API_KEY"] = "testkey"
os.environ["SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402,F401


@pytest.fixture(autouse=True)
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        yield session
