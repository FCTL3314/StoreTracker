from django.contrib import admin

from interactions.comments.admin import ProductCommentAdmin
from products.models import Product, ProductType


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    search_fields = ("name", "slug")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("views",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ("name", "slug")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProductCommentAdmin,)
