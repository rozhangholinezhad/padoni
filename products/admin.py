from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "parent",
        "order",
        "is_active",
        "product_count",
        "created_at",
    )
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("order", "is_active")
    ordering = ("order", "name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "parent", "description", "image"),
        }),
        ("تنظیمات نمایش", {
            "fields": ("is_active", "order"),
        }),
        ("اطلاعات زمانی", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "تعداد محصولات"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "sku",
        "price_display",
        "stock",
        "compatibility",
        "is_active",
        "is_featured",
        "is_available",
        "created_at",
    )
    list_filter = (
        "category",
        "compatibility",
        "is_active",
        "is_featured",
        "is_available",
        "created_at",
    )
    search_fields = ("name", "sku", "slug", "flavor", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("stock", "is_active", "is_featured", "is_available")
    readonly_fields = ("created_at", "updated_at", "final_price_display")
    autocomplete_fields = ("category",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": (
                "category",
                "name",
                "slug",
                "sku",
                "short_description",
                "description",
            ),
        }),
        ("قیمت و موجودی", {
            "fields": (
                "price",
                "discount_price",
                "final_price_display",
                "stock",
            ),
        }),
        ("مشخصات محصول", {
            "fields": (
                "flavor",
                "compatibility",
                "image",
            ),
        }),
        ("وضعیت نمایش", {
            "fields": (
                "is_active",
                "is_available",
                "is_featured",
            ),
        }),
        ("اطلاعات زمانی", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def price_display(self, obj):
        if obj.has_discount:
            return format_html(
                '<span style="text-decoration: line-through; color: #888;">{}</span> '
                '<strong style="color: #c00;">{}</strong> تومان',
                f"{obj.price:,.0f}",
                f"{obj.discount_price:,.0f}",
            )
        return f"{obj.price:,.0f} تومان"
    price_display.short_description = "قیمت"

    def final_price_display(self, obj):
        return f"{obj.final_price:,.0f} تومان"
    final_price_display.short_description = "قیمت نهایی"
