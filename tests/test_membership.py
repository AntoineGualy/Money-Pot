import pytest
from sqlalchemy.exc import IntegrityError

from app import User, Pot, Membership, GroceryItem, db
from conftest import register_user, login


def _user(username):
    return User.query.filter_by(username=username).first()


def _invite_code(pot_name):
    return Pot.query.filter_by(name=pot_name).first().invite_code


def test_user_can_create_pot(app, client):
    register_user(client, "alice")
    alice = _user("alice")

    resp = client.post("/pots/new", data={"name": "Roommates"}, follow_redirects=True)
    assert resp.status_code == 200

    pot = Pot.query.filter_by(name="Roommates").first()
    assert pot is not None
    membership = Membership.query.filter_by(user_id=alice.id, pot_id=pot.id).first()
    assert membership is not None
    assert membership.role == "owner"
    # Registration's personal pot + the new one.
    assert Membership.query.filter_by(user_id=alice.id).count() == 2


def test_second_user_can_join_via_invite_code(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    code = _invite_code("Shared")
    pot = Pot.query.filter_by(name="Shared").first()

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob = _user("bob")

    bob_client.get(f"/join/{code}")
    resp = bob_client.post(f"/join/{code}", follow_redirects=True)
    assert resp.status_code == 200

    membership = Membership.query.filter_by(user_id=bob.id, pot_id=pot.id).first()
    assert membership is not None
    assert membership.role == "member"
    assert Membership.query.filter_by(pot_id=pot.id).count() == 2


def test_duplicate_join_is_idempotent_at_route_level(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    code = _invite_code("Shared")
    pot = Pot.query.filter_by(name="Shared").first()

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob = _user("bob")

    bob_client.post(f"/join/{code}", follow_redirects=True)
    bob_client.post(f"/join/{code}", follow_redirects=True)

    assert Membership.query.filter_by(user_id=bob.id, pot_id=pot.id).count() == 1


def test_duplicate_membership_rejected_at_db_level(app, client):
    register_user(client, "alice")
    alice = _user("alice")
    membership = Membership.query.filter_by(user_id=alice.id).first()

    dup = Membership(user_id=alice.id, pot_id=membership.pot_id, role="member")
    db.session.add(dup)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_leaving_last_pot_yields_new_personal_pot(app, client):
    register_user(client, "alice")
    alice = _user("alice")
    original_pot_id = Membership.query.filter_by(user_id=alice.id).first().pot_id

    # No follow_redirects: chasing the redirect would immediately hit index()
    # and trigger get_active_pot's self-heal as part of this same call,
    # masking the transient zero-membership state we want to check below.
    client.post(f"/pots/{original_pot_id}/leave")
    assert Membership.query.filter_by(user_id=alice.id).count() == 0
    assert Pot.query.get(original_pot_id) is None

    client.get("/")  # triggers get_active_pot's self-heal

    memberships = Membership.query.filter_by(user_id=alice.id).all()
    assert len(memberships) == 1
    assert memberships[0].role == "owner"
    assert Pot.query.get(memberships[0].pot_id) is not None


def test_owner_leaving_transfers_to_longest_standing_member(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()
    code = pot.invite_code

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob = _user("bob")
    bob_client.post(f"/join/{code}", follow_redirects=True)

    client.post(f"/pots/{pot.id}/leave", follow_redirects=True)

    bob_membership = Membership.query.filter_by(user_id=bob.id, pot_id=pot.id).first()
    assert bob_membership.role == "owner"
    assert Pot.query.get(pot.id) is not None


def test_last_member_leaving_deletes_pot_and_its_items(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()

    client.post("/", data={"amount": "10", "category": "produce"}, follow_redirects=True)
    item = GroceryItem.query.filter_by(pot_id=pot.id).first()
    assert item is not None

    client.post(f"/pots/{pot.id}/leave", follow_redirects=True)

    assert Pot.query.get(pot.id) is None
    assert GroceryItem.query.filter_by(pot_id=pot.id).count() == 0
    assert Membership.query.filter_by(pot_id=pot.id).count() == 0


def test_removed_member_self_heals_to_new_personal_pot(app, client):
    # Covers the point-4 fix: a member OTHER than the one acting (the owner,
    # via remove_member) loses their only pot as a side effect, and must
    # self-heal on their own next request - not the acting user's.
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()
    code = pot.invite_code

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob = _user("bob")
    bob_personal_pot_id = Membership.query.filter_by(user_id=bob.id).first().pot_id

    # Bob leaves his personal pot (sole member -> deleted), then joins
    # alice's shared pot, ending up with exactly one membership: Shared.
    # No follow_redirects on the leave call: chasing the redirect would hit
    # index() and self-heal immediately, masking the zero-membership state.
    bob_client.post(f"/pots/{bob_personal_pot_id}/leave")
    bob_client.post(f"/join/{code}", follow_redirects=True)
    assert Membership.query.filter_by(user_id=bob.id).count() == 1

    client.post(f"/pots/{pot.id}/members/{bob.id}/remove", follow_redirects=True)
    assert Membership.query.filter_by(user_id=bob.id).count() == 0

    bob_client.get("/")  # triggers get_active_pot's self-heal for bob

    memberships = Membership.query.filter_by(user_id=bob.id).all()
    assert len(memberships) == 1
    assert memberships[0].role == "owner"
    assert memberships[0].pot_id != pot.id
    new_pot = Pot.query.get(memberships[0].pot_id)
    assert new_pot is not None
    assert new_pot.name == "bob's Pot"
