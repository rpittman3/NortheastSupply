from decimal import Decimal, ROUND_HALF_UP


MONEY = Decimal("0.01")


def money(value):
    """Return a currency-safe Decimal rounded the same way everywhere."""
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def product_price(product, discount=None):
    """Return MAP-first pricing normally, or discounted calculated pricing."""
    if discount is not None:
        if product.price is None:
            return None
        calculated = money(product.price)
        percentage = Decimal(str(discount.percentage))
        return money(calculated * (Decimal("100") - percentage) / Decimal("100"))
    return money(product.display_price) if product.display_price is not None else None


def cart_pricing(cart_items, discount=None):
    """Create authoritative per-item and subtotal values for a cart."""
    item_prices = {}
    subtotal = Decimal("0.00")
    undiscounted_subtotal = Decimal("0.00")
    for item in cart_items:
        if item.product.price is None or item.product.requires_quote:
            raise ValueError(f"{item.product.name} cannot be purchased through checkout.")
        unit_price = (
            product_price(item.product, discount)
            if discount is not None
            else money(item.product.price)
        )
        if unit_price is None:
            unit_price = Decimal("0.00")
        line_total = money(unit_price * item.quantity)
        item_prices[item.id] = {"unit": unit_price, "total": line_total}
        subtotal += line_total
        undiscounted_subtotal += money(item.product.price) * item.quantity
    subtotal = money(subtotal)
    undiscounted_subtotal = money(undiscounted_subtotal)
    return {
        "items": item_prices,
        "subtotal": subtotal,
        "undiscounted_subtotal": undiscounted_subtotal,
        "discount_amount": money(undiscounted_subtotal - subtotal) if discount else Decimal("0.00"),
    }