"""منطق سبد خرید و ساخت سفارش"""

from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404

from products.models import Product

from .models import BankAccount, Cart, CartItem, Order, OrderItem


def get_or_create_cart(request) -> Cart:
    """سبد کاربر لاگین یا سبد مبتنی بر session"""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        # ادغام سبد مهمان در صورت وجود
        session_key = request.session.session_key
        if session_key:
            guest = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
            if guest and guest.pk != cart.pk:
                _merge_carts(guest, cart)
                guest.delete()
        return cart

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


def _merge_carts(source: Cart, target: Cart) -> None:
    for item in source.items.all():
        existing = target.items.filter(product=item.product).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity"])
        else:
            item.cart = target
            item.save(update_fields=["cart"])


def add_to_cart(request, product: Product, quantity: int = 1) -> CartItem:
    cart = get_or_create_cart(request)
    quantity = max(1, int(quantity))
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity"])
    return item


def update_cart_item(cart: Cart, product_id: int, quantity: int) -> None:
    item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    if quantity <= 0:
        item.delete()
    else:
        item.quantity = quantity
        item.save(update_fields=["quantity"])


def remove_from_cart(cart: Cart, product_id: int) -> None:
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()


@transaction.atomic
def create_order_from_cart(
    *,
    user,
    cart: Cart,
    shipping_cost: Decimal = Decimal("0"),
    user_note: str = "",
    receiver_name: str = "",
    receiver_phone: str = "",
    province: str = "",
    city: str = "",
    postal_code: str = "",
    address: str = "",
) -> Order:
    items = list(cart.items.select_related("product"))
    if not items:
        raise ValueError("سبد خرید خالی است.")

    for item in items:
        product = item.product
        if not product.is_in_stock:
            raise ValueError(f"محصول «{product.name}» موجود نیست.")
        if item.quantity > product.stock:
            raise ValueError(
                f"موجودی «{product.name}» کافی نیست (موجودی: {product.stock})."
            )

    subtotal = sum((item.line_total for item in items), Decimal("0"))
    total = subtotal + shipping_cost
    bank = BankAccount.objects.filter(is_active=True).order_by("order").first()

    order = Order.objects.create(
        user=user,
        status=Order.Status.PENDING_PAYMENT,
        payment_method=Order.PaymentMethod.CARD_TO_CARD,
        receiver_name=receiver_name or user.get_shipping_receiver(),
        receiver_phone=receiver_phone or user.get_shipping_phone(),
        province=province or user.province,
        city=city or user.city,
        postal_code=postal_code or user.postal_code,
        address=address or user.address,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        total=total,
        user_note=user_note,
        bank_account=bank,
    )

    for item in items:
        product = item.product
        unit = item.unit_price
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=unit,
            quantity=item.quantity,
            line_total=unit * item.quantity,
        )
        # کاهش موجودی
        product.stock = max(0, product.stock - item.quantity)
        product.save(update_fields=["stock"])

    cart.items.all().delete()
    return order
