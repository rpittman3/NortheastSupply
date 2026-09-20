import os
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:////tmp/session-discount-tests.db"
os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")
os.environ.setdefault("REPL_ID", "test-repl")

import pytest

from app import app, db
import routes  # noqa: F401
from models import CartItem, Category, DiscountCode, Order, Product, User
from pricing import cart_pricing, product_price


@pytest.fixture()
def client():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as test_client:
        yield test_client
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()


def create_catalog():
    category = Category(name="Test", slug="test", markup=Decimal("10"))
    user = User(id="customer-1", email="customer@example.com")
    db.session.add_all([category, user])
    db.session.flush()
    product = Product(
        name="Range",
        slug="range",
        sku="RANGE-1",
        cost=Decimal("50.00"),
        price=Decimal("100.00"),
        map_price=Decimal("140.00"),
        primary_category_id=category.id,
    )
    db.session.add(product)
    db.session.commit()
    return user, product


def test_discount_constraints_and_case_insensitive_admin_crud(client):
    assert client.get("/admin/discount-codes").status_code == 302
    with client.session_transaction() as session:
        session["admin_authenticated"] = True

    response = client.post(
        "/admin/discount-codes/add",
        data={"code": " save10 ", "percentage": "10", "is_active": "y"},
    )
    assert response.status_code == 302
    with app.app_context():
        code = DiscountCode.query.one()
        assert code.code == "SAVE10"
        assert code.percentage == Decimal("10.00")

    response = client.post(
        "/admin/discount-codes/add",
        data={"code": "SaVe10", "percentage": "5", "is_active": "y"},
    )
    assert b"already exists" in response.data

    response = client.post(
        "/admin/discount-codes/add",
        data={"code": "TOO-MUCH", "percentage": "101", "is_active": "y"},
    )
    assert b"Number must be between 0 and 100" in response.data


def test_apply_replace_remove_and_inactive_resolution(client):
    with app.app_context():
        db.session.add_all([
            DiscountCode(code="FIRST", percentage=Decimal("10"), is_active=True),
            DiscountCode(code="SECOND", percentage=Decimal("20"), is_active=True),
        ])
        db.session.commit()

    client.post("/discount-code/apply", data={"code": "first", "next": "/"})
    with client.session_transaction() as session:
        assert session["discount_code"] == "FIRST"

    client.post("/discount-code/apply", data={"code": "SeCoNd", "next": "/"})
    with client.session_transaction() as session:
        assert session["discount_code"] == "SECOND"

    with app.app_context():
        second = DiscountCode.query.filter_by(code="SECOND").one()
        second.is_active = False
        db.session.commit()
    response = client.get("/")
    assert b"no longer valid" in response.data
    with client.session_transaction() as session:
        assert "discount_code" not in session

    client.post("/discount-code/apply", data={"code": "FIRST", "next": "/"})
    client.post("/discount-code/remove", data={"next": "/"})
    with client.session_transaction() as session:
        assert "discount_code" not in session


def test_discounted_price_bypasses_map_and_rounds_line_totals(client):
    with app.app_context():
        _, product = create_catalog()
        discount = DiscountCode(code="THIRD", percentage=Decimal("33.33"), is_active=True)
        db.session.add(discount)
        db.session.flush()
        item = CartItem(user_id="customer-1", product_id=product.id, quantity=3)
        db.session.add(item)
        db.session.commit()

        assert product_price(product) == Decimal("140.00")
        assert product_price(product, discount) == Decimal("66.67")
        pricing = cart_pricing([item], discount)
        assert pricing["subtotal"] == Decimal("200.01")
        assert pricing["undiscounted_subtotal"] == Decimal("300.00")
        assert pricing["discount_amount"] == Decimal("99.99")

        no_code = cart_pricing([item])
        assert no_code["subtotal"] == Decimal("300.00")


def test_discount_never_turns_unpriceable_products_into_free_items(client):
    with app.app_context():
        user, product = create_catalog()
        discount = DiscountCode(code="SAFE", percentage=Decimal("50"), is_active=True)
        db.session.add(discount)
        product.price = None
        product.map_price = Decimal("140.00")
        item = CartItem(user_id=user.id, product_id=product.id, quantity=1)
        db.session.add(item)
        db.session.commit()

        assert product_price(product) == Decimal("140.00")
        assert product_price(product, discount) is None
        with pytest.raises(ValueError):
            cart_pricing([item], discount)

        product.price = Decimal("100.00")
        product.requires_quote = True
        db.session.commit()
        with pytest.raises(ValueError):
            cart_pricing([item], discount)


def test_admin_delete_requires_csrf(client):
    with app.app_context():
        code = DiscountCode(code="KEEP", percentage=Decimal("5"), is_active=True)
        db.session.add(code)
        db.session.commit()
        code_id = code.id
    with client.session_transaction() as session:
        session["admin_authenticated"] = True

    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post(f"/admin/discount-codes/{code_id}/delete")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(DiscountCode, code_id) is not None
    app.config["WTF_CSRF_ENABLED"] = False


def test_order_snapshot_fields_preserve_discounted_item_prices(client, monkeypatch):
    with app.app_context():
        user, product = create_catalog()
        discount = DiscountCode(code="ORDER25", percentage=Decimal("25"), is_active=True)
        db.session.add(discount)
        db.session.flush()
        item = CartItem(user_id=user.id, product_id=product.id, quantity=2)
        db.session.add(item)
        db.session.commit()

    monkeypatch.setattr(routes, "send_order_notification", lambda order, user: None)
    with client.session_transaction() as session:
        session["_user_id"] = "customer-1"
        session["_fresh"] = True
        session["discount_code"] = "ORDER25"

    # The route's auth wrapper expects an OAuth token. Bypass only that wrapper's
    # token-refresh branch while preserving Flask-Login identity behavior.
    process_view = app.view_functions["process_order"]
    app.view_functions["process_order"] = process_view.__wrapped__
    try:
        response = client.post("/process_order", data={
            "shipping_name": "Test Customer",
            "shipping_address": "123 Test Street",
            "shipping_city": "Boston",
            "shipping_state": "MA",
            "shipping_zip": "02108",
            "shipping_phone": "6175550100",
            "shipping_option": "Loading Dock Delivery",
        })
    finally:
        app.view_functions["process_order"] = process_view

    assert response.status_code == 302
    with app.app_context():
        order = Order.query.one()
        assert order.discount_code == "ORDER25"
        assert order.discount_percentage == Decimal("25.00")
        assert order.undiscounted_subtotal == Decimal("200.00")
        assert order.discount_amount == Decimal("50.00")
        assert order.subtotal == Decimal("150.00")
        assert order.items[0].unit_price == Decimal("75.00")
        assert order.items[0].total_price == Decimal("150.00")