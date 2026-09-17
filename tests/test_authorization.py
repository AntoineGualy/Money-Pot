from app import User, Pot, Membership, GroceryItem
from conftest import register_user


def _user(username):
    return User.query.filter_by(username=username).first()


def test_non_member_cannot_edit_or_delete_item(app, client):
    register_user(client, "alice")
    client.post("/", data={"amount": "5", "category": "produce"}, follow_redirects=True)
    alice = _user("alice")
    item = GroceryItem.query.filter_by(added_by_user_id=alice.id).first()

    mallory_client = app.test_client()
    register_user(mallory_client, "mallory")

    resp = mallory_client.post(f"/delete/{item.id}")
    assert resp.status_code == 403
    resp = mallory_client.get(f"/edit/{item.id}")
    assert resp.status_code == 403
    resp = mallory_client.post(f"/edit/{item.id}", data={"func": "99"})
    assert resp.status_code == 403

    assert GroceryItem.query.get(item.id) is not None


def test_member_can_edit_and_delete_any_item_in_their_pot(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()
    code = pot.invite_code
    client.post("/", data={"amount": "5", "category": "produce"}, follow_redirects=True)
    item = GroceryItem.query.filter_by(pot_id=pot.id).first()

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob_client.post(f"/join/{code}", follow_redirects=True)

    resp = bob_client.post(f"/edit/{item.id}", data={"func": "42"}, follow_redirects=True)
    assert resp.status_code == 200
    assert int(GroceryItem.query.get(item.id).amount) == 42

    resp = bob_client.post(f"/delete/{item.id}", follow_redirects=True)
    assert resp.status_code == 200
    assert GroceryItem.query.get(item.id) is None


def test_non_owner_cannot_regenerate_invite(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()
    code = pot.invite_code

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob_client.post(f"/join/{code}", follow_redirects=True)

    resp = bob_client.post(f"/pots/{pot.id}/invite/regenerate")
    assert resp.status_code == 403
    assert Pot.query.get(pot.id).invite_code == code


def test_non_owner_cannot_remove_another_member(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()
    code = pot.invite_code

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob_client.post(f"/join/{code}", follow_redirects=True)

    carol_client = app.test_client()
    register_user(carol_client, "carol")
    carol_client.post(f"/join/{code}", follow_redirects=True)
    carol = _user("carol")

    resp = bob_client.post(f"/pots/{pot.id}/members/{carol.id}/remove")
    assert resp.status_code == 403
    assert Membership.query.filter_by(user_id=carol.id, pot_id=pot.id).first() is not None


def test_any_member_can_set_shared_budget(app, client):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()
    code = pot.invite_code

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob_client.post(f"/join/{code}", follow_redirects=True)

    resp = bob_client.post("/budget", data={"budget": "150"}, follow_redirects=True)
    assert resp.status_code == 200
    assert Pot.query.get(pot.id).budget == 150
