from app import User, Pot, GroceryItem
from conftest import register_user


def _user(username):
    return User.query.filter_by(username=username).first()


def _setup_shared_pot(client, app):
    register_user(client, "alice")
    client.post("/pots/new", data={"name": "Shared"}, follow_redirects=True)
    pot = Pot.query.filter_by(name="Shared").first()

    bob_client = app.test_client()
    register_user(bob_client, "bob")
    bob_client.post(f"/join/{pot.invite_code}", follow_redirects=True)

    return pot, bob_client


def test_members_see_each_others_purchases(app, client):
    pot, bob_client = _setup_shared_pot(client, app)

    client.post("/", data={"amount": "12", "category": "produce"}, follow_redirects=True)

    resp = bob_client.get("/")
    assert resp.status_code == 200
    assert b"produce" in resp.data
    assert b"$12" in resp.data


def test_shared_totals_reflect_all_members_purchases(app, client):
    pot, bob_client = _setup_shared_pot(client, app)

    client.post("/", data={"amount": "10", "category": "produce"}, follow_redirects=True)
    bob_client.post("/", data={"amount": "20", "category": "snacks"}, follow_redirects=True)

    items = GroceryItem.query.filter_by(pot_id=pot.id).all()
    assert sum(item.amount for item in items) == 30

    resp = client.get("/")
    assert b"$30" in resp.data


def test_item_attributed_to_real_logged_in_user(app, client):
    pot, bob_client = _setup_shared_pot(client, app)
    bob = _user("bob")

    bob_client.post("/", data={"amount": "7", "category": "dairy"}, follow_redirects=True)

    item = GroceryItem.query.filter_by(pot_id=pot.id, category="dairy").first()
    assert item.added_by_user_id == bob.id

    resp = client.get("/")
    assert b"bob" in resp.data
