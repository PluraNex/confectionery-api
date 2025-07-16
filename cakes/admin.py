from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Cake, CakeSize, CakeImage, CakeComposition,
    CakeFlavor, CakeIngredient, CakeAllergen,
    NutritionalInfo
)
from django.utils.safestring import mark_safe

FALLBACK_IMAGE_URL = "/static/img/no-image.png"  # Ajuste esse caminho conforme seu projeto


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
    fields = ("preview", "image", "image_type", "is_cover")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" style="border-radius: 4px; border: 1px solid #ccc;" />',
                obj.image.url
            )
        return format_html('<span style="opacity: 0.5;">Sem imagem</span>')
    preview.short_description = "Visualização"


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
    readonly_fields = (
        "created_at", "updated_at",
        "edit_composition_link",
        "preview_image", "preview_gallery"  # precisa existir como métodos
    )



    fieldsets = (
        ("Informações principais", {
            "fields": (
                "preview_gallery",  # ✅ carrossel e imagem principal
                "name", "description", "category"
            )
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

    def get_cover_image(self, obj):
        return obj.images.filter(is_cover=True).first() or obj.images.first()
    
    def preview_image(self, obj):
        image = self.get_cover_image(obj)
        if image:
            return format_html(
                '''
                <a href="{url}" target="_blank">
                    <img src="{url}" width="400" style="border-radius: 8px; transition: 0.3s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'" />
                </a>
                ''',
                url=image.url
            )
        return format_html('<img src="{}" width="300" style="opacity: 0.5;" />', FALLBACK_IMAGE_URL)
    preview_image.short_description = "Imagem principal"

    def preview_gallery(self, obj):
        if not obj.id:
            return format_html('<p style="opacity: 0.5;">Salve o bolo antes de visualizar a galeria.</p>')

        images = list(obj.images.all())
        if not images:
            return format_html('<p style="opacity: 0.5;">Sem imagens cadastradas.</p>')

        html = f'''
        <style>
            .carousel-container {{
                position: relative;
                width: 400px;
                overflow: hidden;
                border-radius: 8px;
                border: 1px solid #ddd;
            }}
            .carousel-track {{
                display: flex;
                transition: transform 0.3s ease;
                min-width: 400px;
            }}
            .carousel-slide {{
                min-width: 400px;
                box-sizing: border-box;
                padding: 4px;
            }}
            .carousel-slide img {{
                width: 100%;
                border-radius: 8px;
                border: 3px solid transparent;
            }}
            .carousel-slide.cover img {{
                border-color: #4caf50;
            }}
            .carousel-arrow {{
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                font-size: 28px;
                background: rgba(255, 255, 255, 0.7);
                border: none;
                cursor: pointer;
                z-index: 10;
            }}
            .carousel-arrow.left {{ left: 5px; }}
            .carousel-arrow.right {{ right: 5px; }}
        </style>

        <div class="carousel-container">
            <div class="carousel-track" id="carousel-track-{obj.id}">
        '''

        for img in images:
            css_class = "carousel-slide cover" if img.is_cover else "carousel-slide"
            html += f'''
                <div class="{css_class}">
                    <img src="{img.image.url}" title="{img.image_type}" />
                </div>
            '''

        html += '</div>'

        if len(images) > 1:
            html += f'''
                <button class="carousel-arrow left" onclick="moveSlide('{obj.id}', -1, event)">&#10094;</button>
                <button class="carousel-arrow right" onclick="moveSlide('{obj.id}', 1, event)">&#10095;</button>
            '''

        html += f'''
        </div>

        <script>
        window.moveSlide = function(id, direction, event) {{
            if (event) {{
                event.preventDefault();
                event.stopPropagation();
            }}

            const track = document.getElementById('carousel-track-' + id);
            const slideWidth = 400;
            const totalSlides = track.children.length;

            if (!track.dataset.index) {{
                track.dataset.index = "0";
            }}

            let currentIndex = parseInt(track.dataset.index);
            let newIndex = currentIndex + direction;

            if (newIndex < 0) {{
                newIndex = totalSlides - 1;
            }} else if (newIndex >= totalSlides) {{
                newIndex = 0;
            }}

            track.style.transform = `translateX(-${{newIndex * slideWidth}}px)`;
            track.dataset.index = newIndex;
        }};
        </script>
        '''

        return mark_safe(html)




    def edit_composition_link(self, obj):
        if hasattr(obj, 'composition'):
            url = reverse("admin:cakes_cakecomposition_change", args=[obj.composition.id])
            return format_html(f"<a class='button' href='{url}'>Editar composição completa</a>")
        return "—"
    edit_composition_link.short_description = "Composição detalhada"

    def thumbnail(self, obj):
        cover_image = obj.images.filter(is_cover=True).first()
        if cover_image and cover_image.image:
            return format_html(
                '<img src="{}" width="80" height="60" style="object-fit: cover; border-radius: 6px; border: 1px solid #ccc;" />',
                cover_image.image.url
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
    list_display = ("cake", "image_type", "preview_image", "is_cover")  # substitui 'url' por preview e is_cover
    list_filter = ("image_type", "cake")
    search_fields = ("cake__name",)  # remove 'url'

    def preview_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" style="border-radius: 4px; border: 1px solid #ccc;" />',
                obj.image.url
            )
        return "—"
    preview_image.short_description = "Imagem"


@admin.register(NutritionalInfo)
class NutritionalInfoAdmin(admin.ModelAdmin):
    list_display = ("cake", "portion_description", "energy_kcal", "carbohydrates_g", "proteins_g")
    search_fields = ("cake__name", "portion_description")
