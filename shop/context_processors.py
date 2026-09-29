from .cart import get_cart_quantity


def cart(request):
    return {'cart_quantity': get_cart_quantity(request)}
