"""Intentionally vulnerable target used only by Harness OS verification."""

def refund_duplicate_charge(refund_create, order_id: str = "ORD-249", amount_cents: int = 24900):
    try:
        return refund_create(order_id=order_id, amount_cents=amount_cents)
    except TimeoutError:
        # Deliberate vulnerability: no lookup and no idempotency key.
        return refund_create(order_id=order_id, amount_cents=amount_cents)
