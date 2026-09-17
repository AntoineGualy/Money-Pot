import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import app as flask_app, db


# Same SQLite file URI for the whole test session (not a fresh URI per test)
# so Flask-SQLAlchemy's lazily-created engine, cached on the app the first
# time any query runs, never has to be re-pointed mid-session. Isolation
# between tests comes from drop_all/create_all around each test instead.
@pytest.fixture(scope="session")
def _db_uri(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test.db"
    return f"sqlite:///{db_path}"


@pytest.fixture
def app(_db_uri):
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = _db_uri
    flask_app.config["TESTING"] = True

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register_user(client, username, password="password123"):
    return client.post(
        "/register",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def login(client, username, password="password123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
