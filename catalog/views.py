from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from accounts.permissions import require_roles

from .forms import ProductForm, ProductVariantForm
from .models import Product, ProductVariant


def _is_staff_or_admin(user) -> bool:
    return (
        user.is_authenticated and user.is_active and user.role in [User.Role.ADMIN, User.Role.STAFF]
    )


def product_list(request):
    """
    List products and active variants.

    Staff/Admin: see all products (active and inactive), along with cost prices
    and management links.
    Customers/Public: see only active products; cost prices are strictly excluded.
    """
    is_staff = _is_staff_or_admin(request.user)

    if is_staff:
        products = Product.objects.prefetch_related("variants").all()
    else:
        products = Product.objects.filter(is_active=True).prefetch_related("variants").all()

    # Sanitized representation for customer/public
    items = []
    for p in products:
        variants = p.variants.all() if is_staff else p.variants.filter(is_active=True)
        item = {
            "id": p.id,
            "name": p.name,
            "product_type": p.get_product_type_display(),
            "sales_price": p.sales_price,
            "notes": p.notes,
            "is_active": p.is_active,
            "variants": [
                {
                    "id": v.id,
                    "name": v.name,
                    "attribute_name": v.attribute_name,
                    "attribute_value": v.attribute_value,
                    "price_extra": v.price_extra,
                    "effective_sales_price": v.effective_sales_price,
                    "is_active": v.is_active,
                }
                for v in variants
            ],
        }
        if is_staff:
            item["cost_price"] = p.cost_price
        items.append(item)

    return render(
        request,
        "catalog/product_list.html",
        {"products": items, "is_staff": is_staff},
    )


def product_detail(request, pk):
    """
    Product detail view.
    Strictly excludes cost_price for customers and unauthenticated visitors.
    """
    is_staff = _is_staff_or_admin(request.user)
    if is_staff:
        product = get_object_or_404(Product.objects.prefetch_related("variants"), pk=pk)
    else:
        product = get_object_or_404(
            Product.objects.filter(is_active=True).prefetch_related("variants"), pk=pk
        )

    variants = product.variants.all() if is_staff else product.variants.filter(is_active=True)

    product_data = {
        "id": product.id,
        "name": product.name,
        "product_type": product.get_product_type_display(),
        "sales_price": product.sales_price,
        "notes": product.notes,
        "is_active": product.is_active,
        "variants": variants,
    }
    if is_staff:
        product_data["cost_price"] = product.cost_price

    return render(
        request,
        "catalog/product_detail.html",
        {"product": product_data, "is_staff": is_staff},
    )


@require_http_methods(["GET", "POST"])
def product_create(request):
    """Admin and internal staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' was created successfully.")
            return redirect("catalog:product_detail", pk=product.pk)
    else:
        form = ProductForm()

    return render(request, "catalog/product_form.html", {"form": form, "title": "New Product"})


@require_http_methods(["GET", "POST"])
def product_edit(request, pk):
    """Admin and internal staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' was updated successfully.")
            return redirect("catalog:product_detail", pk=product.pk)
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "catalog/product_form.html",
        {"form": form, "title": f"Edit {product.name}", "product": product},
    )


@require_http_methods(["GET", "POST"])
def variant_create(request, product_pk):
    """Admin and internal staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    product = get_object_or_404(Product, pk=product_pk)

    if request.method == "POST":
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            messages.success(request, f"Variant '{variant.name}' added to {product.name}.")
            return redirect("catalog:product_detail", pk=product.pk)
    else:
        form = ProductVariantForm()

    return render(
        request,
        "catalog/variant_form.html",
        {"form": form, "product": product, "title": f"Add Variant to {product.name}"},
    )


@require_http_methods(["GET", "POST"])
def variant_edit(request, pk):
    """Admin and internal staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=pk)

    if request.method == "POST":
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Variant '{variant.name}' updated successfully.")
            return redirect("catalog:product_detail", pk=variant.product.pk)
    else:
        form = ProductVariantForm(instance=variant)

    return render(
        request,
        "catalog/variant_form.html",
        {
            "form": form,
            "product": variant.product,
            "title": f"Edit Variant '{variant.name}'",
            "variant": variant,
        },
    )


# ── Customer Management Views (Admin/Staff only) ──────────────────────────


@login_required
def customer_list(request):
    """Admin and Staff view of all registered customers."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    customers = User.objects.filter(role=User.Role.CUSTOMER).order_by("email")
    return render(
        request,
        "catalog/customer_list.html",
        {"customers": customers},
    )


@login_required
def customer_detail(request, pk):
    """Admin and Staff view of a single customer record."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    customer = get_object_or_404(User.objects.filter(role=User.Role.CUSTOMER), pk=pk)
    return render(
        request,
        "catalog/customer_detail.html",
        {"customer": customer},
    )
