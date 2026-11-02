"""Shared Knowledge Hub: sharing liked answers, likes, comments, permissions and tenant isolation
(docs/ORGANISATION_PORTAL.md). Runs against the *_test database (conftest.py)."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.org_helpers import OrgFixtures, headers_for

client = TestClient(app)


@pytest.fixture
def fx():
    fixtures = OrgFixtures()
    yield fixtures
    fixtures.cleanup()


@pytest.fixture
def world(fx):
    """Two active organisations, each with an owner and a member, plus an individual user."""
    org_a, org_b = fx.organisation(), fx.organisation()
    people = {
        "a_owner": fx.user(org=org_a, role="owner"),
        "a_member": fx.user(org=org_a, role="member"),
        "a_other": fx.user(org=org_a, role="member"),
        "b_owner": fx.user(org=org_b, role="owner"),
        "b_member": fx.user(org=org_b, role="member"),
        "individual": fx.user(),
    }
    headers = {key: headers_for(user.id) for key, user in people.items()}
    return {"org_a": org_a, "org_b": org_b, "people": people, "h": headers}


def _share(world, fx, who="a_member", **answer):
    message_id = fx.liked_answer(world["people"][who], **answer)
    response = client.post("/api/org/knowledge", json={"message_id": message_id}, headers=world["h"][who])
    assert response.status_code == 201, response.text
    return message_id, response.json()


def test_share_liked_answer_and_read_it_back(world, fx):
    message_id, detail = _share(world, fx)
    assert detail["question"] == "How do I configure rating in Convergent Charging?"
    assert detail["answer"] == "Use the charge plan in SAP Convergent Charging."  # [E1] stripped
    assert "[E1]" not in detail["answer_preview"]
    assert detail["category"] == "cc" and detail["category_label"] == "Convergent Charging (CC)"
    assert detail["like_count"] == 1 and detail["liked_by_me"] is True  # sharing likes it
    assert detail["can_edit"] is True and detail["comments"] == []
    assert detail["likers"][0]["name"] == world["people"]["a_member"].name
    assert detail["shared_by_name"] == world["people"]["a_member"].name

    listing = client.get("/api/org/knowledge", headers=world["h"]["a_other"]).json()
    assert listing["total"] == 1
    item = listing["items"][0]
    assert item["id"] == detail["id"] and item["liked_by_me"] is False and "answer" not in item

    categories = client.get("/api/org/knowledge/categories", headers=world["h"]["a_other"]).json()
    assert [c["key"] for c in categories] == ["cc", "ci", "som", "fica", "integration", "troubleshooting",
                                              "architecture", "general"]
    assert {c["key"]: c["count"] for c in categories}["cc"] == 1
    assert sum(c["count"] for c in categories) == 1

    ids = client.get("/api/org/knowledge/shared-message-ids", headers=world["h"]["a_member"]).json()
    assert ids == {"message_ids": [message_id]}
    assert client.get("/api/org/knowledge/shared-message-ids", headers=world["h"]["a_other"]).json() == {"message_ids": []}

    duplicate = client.post("/api/org/knowledge", json={"message_id": message_id}, headers=world["h"]["a_member"])
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "This answer is already shared.", "id": detail["id"]}


def test_only_own_liked_assistant_answers_can_be_shared(world, fx):
    unliked = fx.liked_answer(world["people"]["a_member"], feedback=None)
    disliked = fx.liked_answer(world["people"]["a_member"], feedback="down")
    someone_elses = fx.liked_answer(world["people"]["a_other"])
    for message_id in (unliked, disliked, someone_elses, "does-not-exist"):
        response = client.post("/api/org/knowledge", json={"message_id": message_id}, headers=world["h"]["a_member"])
        assert response.status_code == 400, message_id
    # Individual accounts have no hub.
    own = fx.liked_answer(world["people"]["individual"])
    assert client.post("/api/org/knowledge", json={"message_id": own},
                       headers=world["h"]["individual"]).status_code == 403
    assert client.get("/api/org/knowledge", headers=world["h"]["individual"]).status_code == 403
    assert client.get("/api/org/me", headers=world["h"]["individual"]).status_code == 403


def test_search_category_filter_and_pagination(world, fx):
    _share(world, fx, question="Why are billing documents not generated?", answer="Check the billing run log.")
    _share(world, fx, who="a_other", question="Explain dunning for contract accounts", answer="Dunning in FI-CA ...")
    h = world["h"]["a_owner"]
    assert client.get("/api/org/knowledge?category=troubleshooting", headers=h).json()["total"] == 1
    assert client.get("/api/org/knowledge?category=fica", headers=h).json()["total"] == 1
    assert client.get("/api/org/knowledge?category=bogus", headers=h).status_code == 422
    assert client.get("/api/org/knowledge?q=BILLING RUN", headers=h).json()["total"] == 1  # answer text
    assert client.get("/api/org/knowledge?q=dunning", headers=h).json()["total"] == 1
    assert client.get("/api/org/knowledge?q=100%25", headers=h).json()["total"] == 0  # LIKE wildcards escaped
    page = client.get("/api/org/knowledge?limit=1&offset=1", headers=h).json()
    assert page["total"] == 2 and len(page["items"]) == 1
    newest_first = client.get("/api/org/knowledge", headers=h).json()["items"]
    assert newest_first[0]["question"] == "Explain dunning for contract accounts"


def test_likes_are_idempotent(world, fx):
    _, detail = _share(world, fx)
    url = f"/api/org/knowledge/{detail['id']}/like"
    h = world["h"]["a_other"]
    assert client.post(url, headers=h).json() == {"liked": True, "like_count": 2}
    assert client.post(url, headers=h).json() == {"liked": True, "like_count": 2}
    assert client.delete(url, headers=h).json() == {"liked": False, "like_count": 1}
    assert client.delete(url, headers=h).json() == {"liked": False, "like_count": 1}


def test_comments_and_permissions(world, fx):
    _, detail = _share(world, fx)
    base = f"/api/org/knowledge/{detail['id']}"
    comment = client.post(f"{base}/comments", json={"body": "  Helpful, thanks!  "}, headers=world["h"]["a_other"])
    assert comment.status_code == 201
    assert comment.json()["body"] == "Helpful, thanks!" and comment.json()["can_delete"] is True
    assert client.post(f"{base}/comments", json={"body": "   "}, headers=world["h"]["a_other"]).status_code == 422
    assert client.post(f"{base}/comments", json={"body": "x" * 2001}, headers=world["h"]["a_other"]).status_code == 422

    seen_by_sharer = client.get(base, headers=world["h"]["a_member"]).json()
    assert seen_by_sharer["comment_count"] == 1
    assert seen_by_sharer["comments"][0]["can_delete"] is False
    assert client.get(base, headers=world["h"]["a_owner"]).json()["comments"][0]["can_delete"] is True

    comment_id = comment.json()["id"]
    assert client.delete(f"{base}/comments/{comment_id}", headers=world["h"]["a_member"]).status_code == 403
    assert client.delete(f"{base}/comments/{comment_id}", headers=world["h"]["a_owner"]).status_code == 204

    # Category: sharer or org admin; another member cannot.
    assert client.patch(base, json={"category": "ci"}, headers=world["h"]["a_other"]).status_code == 403
    assert client.get(base, headers=world["h"]["a_other"]).json()["can_edit"] is False
    updated = client.patch(base, json={"category": "ci"}, headers=world["h"]["a_member"])
    assert updated.status_code == 200 and updated.json()["category"] == "ci"
    assert client.patch(base, json={"category": "nope"}, headers=world["h"]["a_owner"]).status_code == 422
    assert client.delete(base, headers=world["h"]["a_other"]).status_code == 403
    assert client.delete(base, headers=world["h"]["a_owner"]).status_code == 204
    assert client.get(base, headers=world["h"]["a_member"]).status_code == 404


def test_other_organisations_cannot_reach_answers_comments_or_likes(world, fx):
    _, detail = _share(world, fx)
    base = f"/api/org/knowledge/{detail['id']}"
    comment_id = client.post(f"{base}/comments", json={"body": "internal"}, headers=world["h"]["a_owner"]).json()["id"]
    for key in ("b_owner", "b_member"):
        h = world["h"][key]
        assert client.get(base, headers=h).status_code == 404
        assert client.patch(base, json={"category": "ci"}, headers=h).status_code == 404
        assert client.delete(base, headers=h).status_code == 404
        assert client.post(f"{base}/like", headers=h).status_code == 404
        assert client.delete(f"{base}/like", headers=h).status_code == 404
        assert client.post(f"{base}/comments", json={"body": "hi"}, headers=h).status_code == 404
        assert client.delete(f"{base}/comments/{comment_id}", headers=h).status_code == 404
        listing = client.get("/api/org/knowledge", headers=h).json()
        assert listing["total"] == 0 and listing["items"] == []
        assert all(c["count"] == 0 for c in client.get("/api/org/knowledge/categories", headers=h).json())
    # A comment ID is only valid under its own answer.
    _, other_detail = _share(world, fx, who="b_member")
    assert client.delete(f"/api/org/knowledge/{other_detail['id']}/comments/{comment_id}",
                         headers=world["h"]["b_owner"]).status_code == 404
    # Org B cannot share org A's message either.
    a_message = fx.liked_answer(world["people"]["a_member"])
    assert client.post("/api/org/knowledge", json={"message_id": a_message},
                       headers=world["h"]["b_owner"]).status_code == 400
    assert client.get(base, headers=world["h"]["a_member"]).json()["like_count"] == 1
