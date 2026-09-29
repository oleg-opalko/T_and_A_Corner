"""Small session-backed shopping cart helpers."""

CART_SESSION_ID = 'cart'


def get_cart(request):
    """Return the current cart, normalising data saved in the session."""
    return request.session.get(CART_SESSION_ID, {})


def get_cart_quantity(request):
    return sum(int(quantity) for quantity in get_cart(request).values())


def save_cart(request, cart):
    request.session[CART_SESSION_ID] = cart
    request.session.modified = True
