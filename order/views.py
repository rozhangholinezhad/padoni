from django.shortcuts import render

# Create your views here.
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from products.models import Product

from .forms import CheckoutForm, ReceiptUploadForm
from .models import BankAccount, Order, PaymentReceipt
from .services import (
    add_to_cart,
    create_order_from_cart,
    get_or_create_cart,
    remove_from_cart,
    update_cart_item,
)


class CartDetailView(TemplateView):
    """نمایش سبد خرید"""
    template_name = "order/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_or_create_cart(self.request)
        items = cart.items.select_related("product").all()
        context["cart"] = cart
        context["items"] = items
        context["total"] = cart.total_price
        return context


class AddToCartView(View):
    """افزودن محصول به سبد (POST)"""

    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, slug=kwargs["slug"], is_active=True)
        try:
            qty = int(request.POST.get("quantity", 1))
        except (TypeError, ValueError):
            qty = 1
        if not product.is_in_stock:
            messages.error(request, "این محصول موجود نیست.")
            return redirect(product.get_absolute_url())
        add_to_cart(request, product, qty)
        messages.success(request, f"«{product.name}» به سبد اضافه شد.")
        next_url = request.POST.get("next") or reverse("order:cart")
        return redirect(next_url)


class UpdateCartItemView(View):
    def post(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        product_id = kwargs["product_id"]
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 1
        update_cart_item(cart, product_id, quantity)
        messages.success(request, "سبد به‌روز شد.")
        return redirect("order:cart")


class RemoveCartItemView(View):
    def post(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        remove_from_cart(cart, kwargs["product_id"])
        messages.success(request, "از سبد حذف شد.")
        return redirect("order:cart")


class CheckoutView(LoginRequiredMixin, FormView):
    """ثبت سفارش از روی سبد + آدرس ارسال"""
    template_name = "order/checkout.html"
    form_class = CheckoutForm
    login_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not request.user.check_profile_complete():
            messages.warning(
                request,
                "لطفاً ابتدا اطلاعات پروفایل و آدرس را تکمیل کنید.",
            )
            return redirect("accounts:profile_complete")
        cart = get_or_create_cart(request)
        if not cart.items.exists():
            messages.warning(request, "سبد خرید خالی است.")
            return redirect("order:cart")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        user = self.request.user
        return {
            "receiver_name": user.get_shipping_receiver(),
            "receiver_phone": user.get_shipping_phone(),
            "province": user.province,
            "city": user.city,
            "postal_code": user.postal_code,
            "address": user.address,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_or_create_cart(self.request)
        context["cart"] = cart
        context["items"] = cart.items.select_related("product")
        context["subtotal"] = cart.total_price
        context["shipping_cost"] = Decimal("0")  # بعداً قابل تنظیم
        context["total"] = cart.total_price
        return context

    def form_valid(self, form):
        cart = get_or_create_cart(self.request)
        try:
            order = create_order_from_cart(
                user=self.request.user,
                cart=cart,
                shipping_cost=Decimal("0"),
                **form.cleaned_data,
            )
        except ValueError as exc:
            messages.error(self.request, str(exc))
            return redirect("order:cart")
        messages.success(
            self.request,
            f"سفارش {order.order_number} ثبت شد. لطفاً مبلغ را کارت‌به‌کارت واریز کنید.",
        )
        return redirect("order:payment", order_number=order.order_number)


class PaymentView(LoginRequiredMixin, DetailView):
    """نمایش کارت مقصد + فرم آپلود فیش"""
    model = Order
    template_name = "order/payment.html"
    context_object_name = "order"
    slug_field = "order_number"
    slug_url_kwarg = "order_number"
    login_url = reverse_lazy("accounts:login")

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            "items", "receipts"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bank_accounts"] = BankAccount.objects.filter(is_active=True)
        context["receipt_form"] = ReceiptUploadForm()
        context["latest_receipt"] = self.object.receipts.order_by("-uploaded_at").first()
        return context


class ReceiptUploadView(LoginRequiredMixin, View):
    """آپلود فیش برای سفارش"""
    login_url = reverse_lazy("accounts:login")

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if not order.can_upload_receipt:
            messages.error(request, "برای این سفارش امکان آپلود فیش نیست.")
            return redirect(order.get_absolute_url())

        form = ReceiptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.order = order
            receipt.status = PaymentReceipt.Status.PENDING
            receipt.save()
            order.mark_awaiting_verify()
            messages.success(
                request,
                "فیش ارسال شد. پس از بررسی ادمین، وضعیت سفارش به‌روز می‌شود.",
            )
            return redirect("order:order_detail", order_number=order.order_number)
        messages.error(request, "لطفاً فایل فیش را صحیح انتخاب کنید.")
        return redirect("order:payment", order_number=order.order_number)


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "order/order_list.html"
    context_object_name = "orders"
    login_url = reverse_lazy("accounts:login")

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "order/order_detail.html"
    context_object_name = "order"
    slug_field = "order_number"
    slug_url_kwarg = "order_number"
    login_url = reverse_lazy("accounts:login")

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            "items", "receipts"
        )
