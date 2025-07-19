from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import datetime
from .models import SupplyItem, SupplyBatch, SupplyImage, SupplyNutritionInfo, SupplyIngredientDetail
from commons.enums import get_unit_description
from django.db.models import Min
from django.utils import timezone
from django.urls import path
from supplies.dashboards.views import supplies_dashboard
from stock.services.orchestrator import StockOrchestrator
from django.db.models import Sum


# ----------------------
# Filtros personalizados
# ----------------------

class ExpirationStatusFilter(admin.SimpleListFilter):
    title = "📆 Status de Validade"
    parameter_name = "status_validade"

    def lookups(self, request, model_admin):
        return [
            ("expired", "❌ Vencido"),
            ("expiring_today", "⚠️ Vence Hoje"),
            ("expiring_7", "⚠️ Até 7 dias"),
            ("expiring_30", "⚠️ Até 30 dias"),
            ("valid_long", "✅ Válido (> 30 dias)"),
            ("no_date", "– Sem Data"),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        value = self.value()

        if value == "expired":
            return queryset.filter(expiration_date__lt=today)
        elif value == "expiring_today":
            return queryset.filter(expiration_date=today)
        elif value == "expiring_7":
            return queryset.filter(expiration_date__gt=today, expiration_date__lte=today + datetime.timedelta(days=7))
        elif value == "expiring_30":
            return queryset.filter(expiration_date__gt=today + datetime.timedelta(days=7), expiration_date__lte=today + datetime.timedelta(days=30))
        elif value == "valid_long":
            return queryset.filter(expiration_date__gt=today + datetime.timedelta(days=30))
        elif value == "no_date":
            return queryset.filter(expiration_date__isnull=True)

        return queryset

# ----------------------
# Inline de lotes
# ----------------------

class ReadOnlyBatchInline(admin.TabularInline):
    model = SupplyBatch
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name_plural = "📦 Lotes do Item (visualização somente)"
    readonly_fields = ("batch_code", "expiration_badge", "quantity_badge", "created_at")
    fields = ("batch_code", "expiration_badge", "quantity_badge", "created_at")

    def has_add_permission(self, request, obj):
        return False

    def expiration_badge(self, obj):
        if not obj.expiration_date:
            return format_html('<span style="opacity: 0.5;">–</span>')

        today = timezone.now().date()
        delta = (obj.expiration_date - today).days
        exp_str = obj.expiration_date.strftime("%d/%m/%Y")

        if delta < 0:
            return format_html(
                '<span title="Vencido em {} ({} dias atrás)" style="background:#f8d7da; color:#721c24; padding:2px 8px; border-radius:4px;">❌ Vencido</span>',
                exp_str, abs(delta)
            )
        elif delta <= 7:
            return format_html(
                '<span title="Vence em {} ({} dias)" style="background:#fff3cd; color:#856404; padding:2px 8px; border-radius:4px;">⚠️ {} dias</span>',
                exp_str, delta, delta
            )
        elif delta <= 30:
            return format_html(
                '<span title="Vence em {} ({} dias)" style="background:#d1ecf1; color:#0c5460; padding:2px 8px; border-radius:4px;">📅 {} dias</span>',
                exp_str, delta, delta
            )
        else:
            return format_html(
                '<span title="Vence em {} ({} dias)" style="background:#e2f0d9; color:#155724; padding:2px 8px; border-radius:4px;">✅ {} dias</span>',
                exp_str, delta, delta
            )
    expiration_badge.short_description = "Validade"

    def quantity_badge(self, obj):
        return format_html(
            '<span style="background:#eef; padding:2px 6px; border-radius:4px;">{}</span>',
            obj.quantity
        )
    quantity_badge.short_description = "Qtd"


# ----------------------
# Inline de imagens
# ----------------------

class SupplyImageInline(admin.TabularInline):
    model = SupplyImage
    extra = 1
    show_change_link = False
    fields = ("preview", "image", "image_type", "is_cover")
    readonly_fields = ("preview",)
    verbose_name = "Imagem"
    verbose_name_plural = "🖼️ Imagens"

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" style="border-radius: 4px; border: 1px solid #ccc;" />',
                obj.image.url
            )
        return format_html('<span style="opacity: 0.5;">Sem imagem</span>')
    preview.short_description = "Visualização"

# ----------------------------
# Inline: Nutrição
# ----------------------------
class SupplyNutritionInline(admin.StackedInline):
    model = SupplyNutritionInfo
    extra = 0
    can_delete = False
    verbose_name = "Informação Nutricional"
    verbose_name_plural = "🥦 Informação Nutricional"
    fieldsets = (
        ("Valores Nutricionais por Porção", {
            "fields": (
                "serving_size", "calories",
                "protein", "fat", "saturated_fat", "trans_fat",
                "carbohydrates", "sugars", "fiber", "sodium"
            )
        }),
    )


# ----------------------------
# Inline: Ingredientes e advertências
# ----------------------------
class SupplyIngredientDetailInline(admin.StackedInline):
    model = SupplyIngredientDetail
    extra = 0
    can_delete = False
    verbose_name = "Composição e Advertências"
    verbose_name_plural = "🌿 Composição e Advertências"
    fieldsets = (
        ("Composição e Advertências", {
            "fields": (
                "ingredient_list",
                "contains_gluten",
                "is_vegan",
                "warnings",
            )
        }),
    )



# ----------------------
# Admin de SupplyItem
# ----------------------

@admin.register(SupplyItem)
class SupplyItemAdmin(admin.ModelAdmin):
    list_display = [
        "thumbnail",           # Miniatura
        "name", "sku",         # Nome e código
        "category_badge",      # Categoria com destaque
        "unit_badge",          # Unidade com badge
        "unit_description_display",  # Descrição técnica da unidade

        "nutrition_summary",   # Resumo nutricional
        "ingredient_summary",  # Ingredientes principais
        "has_allergens",       # Alergênicos visíveis
        "is_vegan_display",    # Vegano (✅/❌)

        "next_expiration_date",     # Próxima data de validade
        "expiration_warning",       # Alerta de vencimento (⚠️)
        
        "updated_at_display",  # Última atualização
        "is_active"            # Status de atividade
    ]
    list_filter = [
        "category",
        "unit_of_measure",
        "is_active",
        ("ingredient_detail__contains_gluten", admin.BooleanFieldListFilter),
        ("ingredient_detail__is_vegan", admin.BooleanFieldListFilter),
        ExpirationStatusFilter, 
    ]
    search_fields = ["name", "sku", "barcode"]
    readonly_fields = ["created_at", "updated_at", "preview_image", "preview_grid"]
    ordering = ["name"]
    inlines = [ReadOnlyBatchInline, SupplyImageInline, SupplyNutritionInline, SupplyIngredientDetailInline  ]
    actions = ["desativar_itens"]

    fieldsets = (
        ("🧾 Identificação e Classificação", {
            "fields": (
                "name", "sku", "barcode", "description",
                "category", "unit_of_measure", "origin_country",
                "regulatory_code", "tags"
            )
        }),
        ("📸 Galeria do Produto", {
            "fields": ("preview_image", "preview_grid"),
            "classes": ("collapse",)
        }),
        ("⚙️ Controles Operacionais", {
            "fields": (
                "expiration_control", "batch_control",
                "is_ingredient", "is_active"
            )
        }),
        ("📆 Auditoria", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


    def desativar_itens(self, request, queryset):
        queryset.update(is_active=False)
    desativar_itens.short_description = "Desativar itens selecionados"

    def unit_description_display(self, obj):
        return get_unit_description(obj.unit_of_measure)
    unit_description_display.short_description = "Descrição da Unidade"

    def get_cover_image(self, obj):
        return obj.images.filter(is_cover=True).first() or obj.images.first()

    def preview_image(self, obj):
        image = self.get_cover_image(obj)
        if image:
            return format_html(
                '<img src="{}" width="400" style="border-radius: 8px; border: 1px solid #ccc;" />',
                image.image.url
            )
        return format_html('<span style="opacity: 0.5;">Sem imagem</span>')
    preview_image.short_description = "Imagem Principal"

    def preview_grid(self, obj):
        if not obj.id:
            return format_html('<p style="opacity: 0.5;">Salve antes para visualizar as imagens.</p>')

        images_by_type = {img.image_type: img for img in obj.images.all()}
        image_types = [
            ("embalagem", "Embalagem"),
            ("rotulo", "Rótulo"),
            ("detalhe", "Detalhe"),
            ("contexto", "Contexto"),
        ]

        html = """<table class='preview-table'><thead><tr>"""
        for _, label in image_types:
            html += f"<th>{label}</th>"
        html += "</tr></thead><tbody><tr>"

        for key, _ in image_types:
            img = images_by_type.get(key)
            if img:
                td_class = "cover" if img.is_cover else ""
                html += f'''<td class="{td_class}"><a href="{img.image.url}" target="_blank"><img src="{img.image.url}" alt="{img.image_type}" title="{img.get_image_type_display()}" /></a></td>'''
            else:
                html += '<td><span style="opacity: 0.3;">–</span></td>'

        html += "</tr></tbody></table>"
        return mark_safe(html)
    preview_grid.short_description = "Galeria por Tipo"

    def thumbnail(self, obj):
        image = self.get_cover_image(obj)
        if image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 6px;" />',
                image.image.url
            )
        return "-"
    thumbnail.short_description = "Imagem"

    def category_badge(self, obj):
        return format_html('<span style="background:#eef;padding:2px 6px;border-radius:4px;">{}</span>', obj.get_category_display())
    category_badge.short_description = "Categoria"

    def unit_badge(self, obj):
        return format_html('<span style="background:#efe;padding:2px 6px;border-radius:4px;">{}</span>', obj.unit_of_measure)
    unit_badge.short_description = "Unidade"

    def nutrition_summary(self, obj):
        if hasattr(obj, "nutrition_info"):
            return obj.nutrition_info.summary()
        return "-"
    nutrition_summary.short_description = "Nutrição"

    def ingredient_summary(self, obj):
        if hasattr(obj, "ingredient_detail"):
            return obj.ingredient_detail.short_ingredients(10)
        return "-"
    ingredient_summary.short_description = "Ingredientes"

    def expiration_warning(self, obj):
        next_exp = obj.next_expiration()
        
        if obj.has_expiration() and next_exp:
            today = timezone.now().date()  # ← ADICIONE ESTA LINHA
            days_left = (next_exp - today).days
            exp_date_str = next_exp.strftime("%d/%m/%Y") 

            if days_left < 0:
                return format_html(
                    '<span title="Produto vencido em {} (há {} dias)" '
                    'style="background:#f8d7da; color:#721c24; padding:3px 8px; border-radius:4px;">'
                    'Vencido</span>',
                    exp_date_str, abs(days_left)
                )
            elif days_left <= 7:
                return format_html(
                    '<span title="Produto vence em {} ({} dias restantes)" '
                    'style="background:#fff3cd; color:#856404; padding:3px 8px; border-radius:4px;">'
                    '{} dias</span>',
                    exp_date_str, days_left, days_left
                )
            elif days_left <= 30:
                return format_html(
                    '<span title="Produto vence em {} ({} dias restantes)" '
                    'style="background:#d1ecf1; color:#0c5460; padding:3px 8px; border-radius:4px;">'
                    '{} dias</span>',
                    exp_date_str, days_left, days_left
                )
            else:
                return format_html(
                    '<span title="Produto com vencimento em {} ({} dias restantes)" '
                    'style="background:#e2f0d9; color:#155724; padding:3px 8px; border-radius:4px;">'
                    '{} dias</span>',
                    exp_date_str, days_left, days_left
                )

        return format_html(
            '<span title="Sem data de vencimento disponível" style="opacity:0.5;">–</span>'
        )


    expiration_warning.short_description = "Validade"


    def next_expiration_date(self, obj):
        next_exp = obj.next_expiration()
        if next_exp:
            return next_exp.strftime("%d/%m/%Y")
        return "-"
    next_expiration_date.short_description = "Próx. Vencimento"

    def has_allergens(self, obj):
        if hasattr(obj, "ingredient_detail"):
            return obj.ingredient_detail.contains_gluten
        return False
    has_allergens.short_description = "Contém Glúten"
    has_allergens.boolean = True

    def is_vegan_display(self, obj):
        if hasattr(obj, "ingredient_detail"):
            return obj.ingredient_detail.is_vegan
        return False
    is_vegan_display.short_description = "Vegano"
    is_vegan_display.boolean = True  # ✅ usa ícones padrão do Django


    def updated_at_display(self, obj):
        return obj.updated_at.strftime("%d/%m/%Y %H:%M")
    
    updated_at_display.short_description = "Última Atualização"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(supplies_dashboard), name='supplies-dashboard'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['custom_dashboard_button'] = format_html(
            '<a class="button" href="{}">📊 Ver Dashboard</a>',
            '/admin/supplies/supplyitem/dashboard/',
        )
        return super().changelist_view(request, extra_context=extra_context)


# ----------------------
# Admin de SupplyBatch
# ----------------------

from django.utils.html import format_html
from django.utils.timezone import now
from stock.services.orchestrator import StockOrchestrator


@admin.register(SupplyBatch)
class SupplyBatchAdmin(admin.ModelAdmin):
    list_display = [
        "supply_item_link",
        "batch_code",
        "expiration_badge",
        "quantity",
        "stock_status_badge",
        "created_at",
        "ativo_badge"

    ]
    list_filter = [ExpirationStatusFilter]
    search_fields = ["batch_code", "supply_item__name"]
    autocomplete_fields = ["supply_item"]
    readonly_fields = ["created_at"]
    date_hierarchy = "expiration_date"
    actions = ["force_stock_entry"]

    def ativo_badge(self, obj):
        return "✅" if obj.is_active else "❌"
    ativo_badge.short_description = "Ativo?"

    @admin.display(description="Item de Suprimento")
    def supply_item_link(self, obj):
        return format_html(
            '<a href="/admin/supplies/supplyitem/{}/change/">{}</a>',
            obj.supply_item.id,
            obj.supply_item.name
        )

    @admin.display(description="Validade")
    def expiration_badge(self, obj):
        if not obj.expiration_date:
            return format_html('<span style="opacity: 0.6;">–</span>')

        delta = (obj.expiration_date - now().date()).days
        color, label = "#d4edda", f"✅ {delta} dias"

        if delta < 0:
            color, label = "#f8d7da", f"❌ Vencido"
        elif delta <= 7:
            color, label = "#fff3cd", f"⚠️ {delta} dias"
        elif delta <= 30:
            color, label = "#d1ecf1", f"📅 {delta} dias"

        return format_html(
            '<span style="padding:2px 6px; border-radius:4px; background:{};">{}</span>',
            color, label
        )

    @admin.display(description="Estoque")
    def stock_status_badge(self, obj):
        total_in_stock = obj.stock_items.aggregate(total=Sum("quantity"))["total"] or 0

        if total_in_stock == 0:
            return format_html('<span style="color:#721c24;">🚫 Sem estoque</span>')
        elif total_in_stock < obj.quantity:
            return format_html('<span style="color:#856404;">🔄 Parcial: {}</span>', total_in_stock)
        else:
            return format_html('<span style="color:#155724;">✅ Completo: {}</span>', total_in_stock)

    @admin.action(description="📦 Forçar entrada no estoque")
    def force_stock_entry(self, request, queryset):
        count = 0
        for batch in queryset:
            if StockOrchestrator.force_entry(batch):
                count += 1
        self.message_user(
            request,
            f"✅ {count} lote(s) inserido(s) manualmente no estoque com sucesso."
        )
    
    @admin.action(description="❌ Desativar lote(s)")
    def desativar_lotes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} lote(s) desativado(s).")

    actions = ["force_stock_entry", "desativar_lotes"]
