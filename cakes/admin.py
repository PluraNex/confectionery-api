from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Cake, CakeSize, CakeImage, CakeComposition,
    CakeFlavor, CakeIngredient, CakeAllergen,
    NutritionalInfo
)

# ---------- Subinlines da Composição (usados em CakeCompositionAdmin) ---------- #

class CakeFlavorInline(admin.TabularInline):
    model = CakeFlavor
    extra = 1
    min_num = 1
    verbose_name = "Sabor"
    verbose_name_plural = "Sabores"

class CakeIngredientInline(admin.TabularInline):
    model = CakeIngredient
    extra = 1
    verbose_name = "Ingrediente"
    verbose_name_plural = "Ingredientes"

class CakeAllergenInline(admin.TabularInline):
    model = CakeAllergen
    extra = 1
    verbose_name = "Alergênico"
    verbose_name_plural = "Alergênicos"

# ---------- Inlines principais usados no Cake ---------- #

class CakeCompositionInline(admin.StackedInline):
    model = CakeComposition
    extra = 0
    max_num = 1
    show_change_link = True
    fieldsets = (
        (None, {
            "fields": ("topping",),
            "description": "Composição principal (somente topping — edite sabores e ingredientes no botão abaixo)"
        }),
    )

class CakeSizeInline(admin.TabularInline):
    model = CakeSize
    extra = 1
    min_num = 1
    show_change_link = False

class CakeImageInline(admin.TabularInline):
    model = CakeImage
    extra = 1
    show_change_link = False

class NutritionalInfoInline(admin.StackedInline):
    model = NutritionalInfo
    extra = 0
    max_num = 1
    show_change_link = False

# ---------- Botão: editar composição detalhada ---------- #

def edit_composition_link(self, obj):
    if hasattr(obj, 'composition'):
        url = reverse("admin:cakes_cakecomposition_change", args=[obj.composition.id])
        return format_html(f"<a class='button' href='{url}'>Editar composição completa</a>")
    return "—"
edit_composition_link.short_description = "Composição detalhada"

# ---------- Admin principal do Cake ---------- #



@admin.register(Cake)
class CakeAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail", "name", "category", "customizable",
        "is_active", "is_available_for_delivery", "is_available_for_pickup",
        "production_time_days", "edit_composition_link"
    )
    list_filter = ("category", "customizable", "is_active")
    search_fields = ("name", "description", "internal_notes")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "edit_composition_link")

    fieldsets = (
        ("Informações principais", {
            "fields": ("name", "description", "category")
        }),
        ("Configurações", {
            "fields": ("customizable", "estimated_weight_kg", "production_time_days")
        }),
        ("Disponibilidade", {
            "fields": ("is_available_for_delivery", "is_available_for_pickup", "is_active")
        }),
        ("Notas internas", {
            "fields": ("internal_notes",)
        }),
        ("Links úteis", {
            "fields": ("edit_composition_link",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    inlines = [
        CakeCompositionInline,
        CakeSizeInline,
        CakeImageInline,
        NutritionalInfoInline
    ]

    def edit_composition_link(self, obj):
        if hasattr(obj, 'composition'):
            url = reverse("admin:cakes_cakecomposition_change", args=[obj.composition.id])
            return format_html(f"<a class='button' href='{url}'>Editar composição completa</a>")
        return "—"
    edit_composition_link.short_description = "Composição detalhada"

    def thumbnail(self, obj):
        first_image = obj.images.first()
        if first_image:
            return format_html(
                '''
                <div class="thumbnail-wrapper" style="position: relative; display: inline-block;">
                    <img src="{url}" width="80" style="border-radius: 6px;" />
                    <div class="thumbnail-preview" style="
                        display: none;
                        position: absolute;
                        top: 0;
                        left: 90px;
                        z-index: 100;
                        border: 1px solid #ccc;
                        background-color: #fff;
                        padding: 4px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    ">
                        <img src="{url}" width="250" style="border-radius: 6px;" />
                    </div>
                </div>
                <script id="thumbnail-script">
                if (!window.__thumbnailHoverBound) {{
                    document.addEventListener("DOMContentLoaded", function () {{
                        document.querySelectorAll(".thumbnail-wrapper").forEach(function (el) {{
                            el.addEventListener("mouseover", () => {{
                                const preview = el.querySelector(".thumbnail-preview");
                                if (preview) preview.style.display = "block";
                            }});
                            el.addEventListener("mouseout", () => {{
                                const preview = el.querySelector(".thumbnail-preview");
                                if (preview) preview.style.display = "none";
                            }});
                        }});
                    }});
                    window.__thumbnailHoverBound = true;
                }}
                </script>
                ''',
                url=first_image.url
            )
        return "—"

        thumbnail.short_description = "Imagem"


# ---------- Admin completo para composição detalhada ---------- #

@admin.register(CakeComposition)
class CakeCompositionAdmin(admin.ModelAdmin):
    list_display = ("cake", "topping")
    search_fields = ("cake__name", "topping")
    inlines = [
        CakeFlavorInline,
        CakeIngredientInline,
        CakeAllergenInline
    ]


# ---------- Admins auxiliares ---------- #

@admin.register(CakeSize)
class CakeSizeAdmin(admin.ModelAdmin):
    list_display = ("description", "serves", "cake")
    list_filter = ("cake",)
    search_fields = ("cake__name", "description")

@admin.register(CakeImage)
class CakeImageAdmin(admin.ModelAdmin):
    list_display = ("cake", "image_type", "url")
    list_filter = ("image_type", "cake")
    search_fields = ("cake__name", "url")

@admin.register(NutritionalInfo)
class NutritionalInfoAdmin(admin.ModelAdmin):
    list_display = ("cake", "portion_description", "energy_kcal", "carbohydrates_g", "proteins_g")
    search_fields = ("cake__name", "portion_description")
