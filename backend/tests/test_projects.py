"""Projects are stored on the server, and a chat started in a project is saved in it (owner request 2026-11-04).
Runs against the *_test database (conftest.py)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from backend.app.database import SessionLocal, engine
from backend.app.main import app
from backend.app.models.chat import Chat
from backend.tests.org_helpers import OrgFixtures, headers_for

client = TestClient(app)
PROJECT_FIELDS = {"id", "name", "description", "is_pinned", "created_at", "updated_at", "chat_count"}


@pytest.fixture
def fx():
    fixtures = OrgFixtures()
    yield fixtures
    fixtures.cleanup()


def _create(user, **body):
    return client.post("/api/projects", headers=headers_for(user.id), json={"name": "Billing rollout", **body})


def _chat(user, project_id=None, title="Invoice run"):
    body = {"title": title} if project_id is None else {"title": title, "project_id": project_id}
    return client.post("/api/chats", headers=headers_for(user.id), json=body)


def test_projects_are_created_listed_updated_and_private(fx):
    alice, bob = fx.user(), fx.user()
    created = _create(alice, description="FI-CA go-live", is_pinned=True)
    assert created.status_code == 201, created.text
    project = created.json()
    assert set(project) == PROJECT_FIELDS
    assert (project["name"], project["description"], project["is_pinned"], project["chat_count"]) == (
        "Billing rollout", "FI-CA go-live", True, 0)

    assert [p["id"] for p in client.get("/api/projects", headers=headers_for(alice.id)).json()] == [project["id"]]
    assert client.get("/api/projects", headers=headers_for(bob.id)).json() == []

    renamed = client.patch(f"/api/projects/{project['id']}", headers=headers_for(alice.id),
                           json={"name": "  Billing go-live  ", "is_pinned": False})
    assert renamed.status_code == 200, renamed.text
    assert (renamed.json()["name"], renamed.json()["is_pinned"]) == ("Billing go-live", False)
    assert renamed.json()["description"] == "FI-CA go-live", "fields left out are unchanged"

    # Another account can neither change nor delete it.
    assert client.patch(f"/api/projects/{project['id']}", headers=headers_for(bob.id),
                        json={"name": "Mine now"}).status_code == 404
    assert client.delete(f"/api/projects/{project['id']}", headers=headers_for(bob.id)).status_code == 404
    assert client.get("/api/projects", headers=headers_for(alice.id)).json()[0]["name"] == "Billing go-live"


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}, {"name": "x" * 101},
                                  {"name": "Billing", "description": "d" * 501}])
def test_project_input_is_validated(fx, body):
    user = fx.user()
    assert client.post("/api/projects", headers=headers_for(user.id), json=body).status_code == 422


def test_projects_need_a_signed_in_user():
    assert client.get("/api/projects").status_code == 401


def test_a_chat_started_in_a_project_is_stored_in_it(fx):
    alice = fx.user()
    project = _create(alice).json()

    in_project = _chat(alice, project["id"])
    assert in_project.status_code == 201, in_project.text
    assert in_project.json()["project_id"] == project["id"]
    plain = _chat(alice, title="Other question").json()
    assert plain["project_id"] is None

    listed = client.get(f"/api/chats?project_id={project['id']}", headers=headers_for(alice.id)).json()
    assert [chat["id"] for chat in listed] == [in_project.json()["id"]]
    assert listed[0]["project_id"] == project["id"]

    everything = {chat["id"] for chat in client.get("/api/chats", headers=headers_for(alice.id)).json()}
    assert {in_project.json()["id"], plain["id"]} <= everything, "project chats stay in the normal chat list"
    assert client.get("/api/projects", headers=headers_for(alice.id)).json()[0]["chat_count"] == 1


def test_chats_cannot_be_put_in_someone_elses_project(fx):
    alice, bob = fx.user(), fx.user()
    project = _create(alice).json()
    assert _chat(bob, project["id"]).status_code == 404
    assert _chat(bob, "no-such-project").status_code == 404
    assert client.get(f"/api/chats?project_id={project['id']}", headers=headers_for(bob.id)).json() == []


def test_deleting_a_project_keeps_its_chats(fx):
    alice = fx.user()
    project = _create(alice).json()
    chat = _chat(alice, project["id"], title="Keep me").json()

    assert client.delete(f"/api/projects/{project['id']}", headers=headers_for(alice.id)).status_code == 204
    assert client.get("/api/projects", headers=headers_for(alice.id)).json() == []
    with SessionLocal() as db:
        stored = db.get(Chat, chat["id"])
        assert stored is not None and stored.project_id is None


def test_migration_links_chats_to_projects():
    inspector = inspect(engine)
    assert inspector.has_table("projects")
    assert "project_id" in {column["name"] for column in inspector.get_columns("chats")}
    links = [fk for fk in inspector.get_foreign_keys("chats") if fk["referred_table"] == "projects"]
    assert links and links[0]["options"].get("ondelete") == "SET NULL", "deleting a project keeps its chats"
    owners = [fk for fk in inspector.get_foreign_keys("projects") if fk["referred_table"] == "users"]
    assert owners and owners[0]["options"].get("ondelete") == "CASCADE"
