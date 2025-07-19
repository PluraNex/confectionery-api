from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import (
    StockLocation, StockItem, StockMovement, StockThreshold,
    StockMovementType, StockAdjustmentReason
)
from django.db.models import Sum
from stock.forms import StockMovementAdminForm
from simple_history.admin import SimpleHistoryAdmin
from simple_history.utils import update_change_reason
from import_export.admin import ExportMixin
from import_export import resources, fields


class RecentMovementFilter(admin.SimpleListFilter):
    title = "📆 Movimentado nos últimos"
    parameter_name = "recent_days"

    def lookups(self, request, model_admin):
        return [
            ("7", "7 dias"),
            ("30", "30 dias"),
            ("90", "90 dias"),
        ]

    def queryset(self, request, queryset):
        if self.value():
            try:
                days = int(self.value())
                since = timezone.now() - timezone.timedelta(days=days)
                return queryset.filter(date__gte=since)
            except ValueError:
                pass
        return queryset

# 1. Resource para exportação CSV/Excel
class StockMovementResource(resources.ModelResource):
    stock_item_name = fields.Field(attribute="stock_item__object_name", column_name="Item")
    location = fields.Field(attribute="location_display", column_name="Local")
    user = fields.Field(column_name="Usuário")

    def dehydrate_user(self, obj):
        # Pega do histórico
        last = obj.history.last()
        return getattr(last, 'history_user', None)
    
    def dehydrate_movement_type(self, obj):
        return obj.get_movement_type_display()

    class Meta:
        model = StockMovement
        fields = (
            "date", "movement_type", "quantity",
            "stock_item_name", "location", "before_quantity", "after_quantity", "user"
        )


# -------------------------------
# Filtros estratégicos
# -------------------------------

class ExpirationStatusFilter(admin.SimpleListFilter):
    title = "📆 Status de Validade"
    parameter_name = "exp_status"

    def lookups(self, request, model_admin):
        return [
            ("expired", "❌ Vencido"),
            ("expiring_7", "⚠️ Expira em até 7 dias"),
            ("expiring_30", "⚠️ Expira em até 30 dias"),
            ("valid", "✅ Válido (>30 dias)"),
            ("nodate", "– Sem Data"),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == "expired":
            return queryset.filter(supply_batch__expiration_date__lt=today)
        elif self.value() == "expiring_7":
            return queryset.filter(supply_batch__expiration_date__range=[today, today + timezone.timedelta(days=7)])
        elif self.value() == "expiring_30":
            return queryset.filter(supply_batch__expiration_date__range=[today, today + timezone.timedelta(days=30)])
        elif self.value() == "valid":
            return queryset.filter(supply_batch__expiration_date__gt=today + timezone.timedelta(days=30))
        elif self.value() == "nodate":
            return queryset.filter(supply_batch__expiration_date__isnull=True)


# -------------------------------
# Inline: Movimentações em Estoque
# -------------------------------

class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = ("movement_type", "quantity", "date", "source_location", "destination_location", "reference", "notes")
    can_delete = False
    show_change_link = True
    verbose_name_plural = "📦 Histórico de Movimentações"


# -------------------------------
# Admin: Itens de Estoque
# -------------------------------

class MovementOciosoFilter(admin.SimpleListFilter):
    title = "😴 Sem movimento há"
    parameter_name = "dias_sem_movimento"

    def lookups(self, request, model_admin):
        return [("15", "≥ 15 dias"), ("30", "≥ 30 dias"), ("60", "≥ 60 dias")]

    def queryset(self, request, queryset):
        if self.value():
            dias = int(self.value())
            cutoff = timezone.now() - timezone.timedelta(days=dias)
            return queryset.filter(last_movement_date__lt=cutoff)

class AlertThresholdFilter(admin.SimpleListFilter):
    title = "🚨 Alerta Estoque"
    parameter_name = "estoque_alerta"

    def lookups(self, request, model_admin):
        return [("baixo", "Abaixo do mínimo")]

    def queryset(self, request, queryset):
        if self.value() == "baixo":
            return queryset.filter(quantity__lt=models.F("supply_item__threshold__min_quantity"))
        return queryset


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = (
         "image_preview","object_name", "batch_code", "location_display", "quantity_display",
        "unit_display", "expiration_badge", "stock_status_badge",
        "last_movement_date", "giro_badge", "ocioso_badge", "insights_badge"
    )
    list_filter = ("location", ExpirationStatusFilter, MovementOciosoFilter, AlertThresholdFilter)
    search_fields = ("supply_item__name", "supply_batch__batch_code", "location__name", "name", "ean", "description")
    readonly_fields = ("created_at", "updated_at", "recalculated_info")
    autocomplete_fields = ["supply_item"]
    inlines = [StockMovementInline]
    actions = ["recalcular_estoque_em_lote"]

    fieldsets = (
        ("Informações Gerais", {
            "fields": ("supply_item", "supply_batch", "location", "quantity", "unit_of_measure")
        }),
        ("Produção", {
            "fields": ("production_batch",)
        }),
        ("Dados Internos", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at", "recalculated_info")
        }),
    )


    @admin.display(description="📦 Quantidade")
    def quantity_display(self, obj):
        cor = "#dc3545" if obj.quantity <= 0 else "#28a745"
        
        try:
            quantidade = float(obj.quantity)
        except (TypeError, ValueError):
            quantidade = 0.0

        unidade = str(obj.effective_unit or "")

        valor_formatado = f"{quantidade:.2f}"

        return format_html(
            '<span style="color:{}; font-weight:bold;">{} {}</span>',
            cor, valor_formatado, unidade
        )



    @admin.display(description="📏 Unidade")
    def unit_display(self, obj):
        return format_html('<span title="Unidade de medida">{}</span>', obj.get_unit_of_measure_display() or "–")

    
    @admin.display(description="📍 Local")
    def location_display(self, obj):
        return format_html('<span title="Local de armazenamento">{}</span>', obj.location.name if obj.location else "–")


    @admin.display(description="⏳ Validade", ordering="supply_batch__expiration_date")
    def expiration_badge(self, obj):
        if obj.expiration_date:
            days = obj.days_to_expire
            cor = "#dc3545" if obj.is_expired else "#ffc107" if days <= 7 else "#28a745"
            texto = "❌ Vencido" if obj.is_expired else f"⚠️ {days}d" if days <= 7 else f"✅ {days}d"
            return format_html(
                '<span style="padding:2px 8px; border-radius:12px; background:{}; color:white;">{}</span>',
                cor, texto
            )
        return "–"

    @admin.display(description="📊 Status")
    def stock_status_badge(self, obj):
        status = obj.stock_status
        cores = {
            "VENCIDO": "#dc3545",
            "EXPIRANDO": "#ffc107",
            "EM FALTA": "#6c757d",
            "EM ALERTA": "#fd7e14",
            "OK": "#28a745",
        }
        icones = {
            "VENCIDO": "❌",
            "EXPIRANDO": "⚠️",
            "EM FALTA": "📉",
            "EM ALERTA": "⚠️",
            "OK": "✅",
        }
        cor = cores.get(status, "#17a2b8")
        icone = icones.get(status, "ℹ️")
        return format_html('<b style="color:{};">{} {}</b>', cor, icone, status)

    @admin.display(description="📈 Insights")
    def insights_badge(self, obj):
        dias = obj.estimated_days_remaining or 0
        media = obj.average_daily_usage or 0

        if dias == 0:
            return "–"

        try:
            media_float = float(media)
        except (ValueError, TypeError):
            media_float = 0.0

        cor = "#ffc107" if dias < 5 else "#28a745" if dias < 30 else "#17a2b8"
        tooltip = f"Consumo médio: {media_float:.2f}/dia. Estimativa: {dias} dias restantes."

        return format_html(
            '<span title="{}" style="padding:2px 8px; border-radius:12px; background:{}; color:white;">🕓 {}d</span>',
            tooltip, cor, dias
        )


    @admin.display(description="📄 Info Atualizada")
    def recalculated_info(self, obj):
        return mark_safe(f"""
            <ul style='margin:0;padding-left:1em;'>
                <li>💡 <b>Total Entradas:</b> {obj.total_in:.2f}</li>
                <li>📤 <b>Total Saídas:</b> {obj.total_out:.2f}</li>
                <li>📊 <b>Média diária (30d):</b> {obj.average_daily_usage:.2f}</li>
                <li>🕓 <b>Est. dias restantes:</b> {obj.estimated_days_remaining or '–'}</li>
            </ul>
        """)

    @admin.action(description="🔁 Recalcular estoque selecionado")
    def recalcular_estoque_em_lote(self, request, queryset):
        for item in queryset:
            item.recalculate_stock()
        self.message_user(request, f"Estoque recalculado para {queryset.count()} item(ns).")
    
    @admin.display(description="🔄 Giro (30d)")
    def giro_badge(self, obj):
        count = obj.movements.filter(date__gte=timezone.now() - timezone.timedelta(days=30)).count()
        cor = "#28a745" if count > 10 else "#ffc107" if count > 3 else "#dc3545"
        return format_html('<span style="color:{};">{} movs</span>', cor, count)

    @admin.display(description="😴 Ociosidade")
    def ocioso_badge(self, obj):
        dias = (timezone.now().date() - obj.last_movement_date.date()).days if obj.last_movement_date else None
        if dias is None:
            return "-"
        cor = "#dc3545" if dias > 30 else "#ffc107" if dias > 14 else "#28a745"
        return format_html('<span title="{} dias sem movimentação" style="color:{};">{}d</span>', dias, cor, dias)

    @admin.display(description="🧾 Item")
    def object_name(self, obj):
        item = obj.resolved_supply_item
        if not item:
            return "-"
        tooltip = f"ID: {item.id} | Categoria: {item.category} | Unidade: {obj.effective_unit}"
        if item.description:
            tooltip += f" | {item.description}"
        return format_html('<span title="{}">{}</span>', tooltip, item.name)

    
    @admin.display(description="🖼️")
    def image_preview(self, obj):
        item = obj.resolved_supply_item
        if item and item.has_image:
            return mark_safe(item.render_image_thumb())
        return "-"

# -------------------------------
# Admin: Movimentações
# -------------------------------

@admin.register(StockMovement)
class StockMovementAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = StockMovementResource
    form = StockMovementAdminForm

    list_display = (
        "date", "movement_type_badge", "quantity", "batch_code", "stock_item","estoque_tooltip",
        "location_display", "post_movement_balance", "production_order", "movement_summary", "user_display", "was_adjusted", "history_button"
    )
    list_filter = (
        "movement_type", "adjustment_reason",
        "source_location", "destination_location", RecentMovementFilter
    )
    search_fields = (
        "stock_item__supply_item__name",
        "stock_item__supply_batch__batch_code",
        "reference", "notes"
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-date",)
    history_list_display = ["history_date", "history_user", "history_type", "diff_display"]
    list_select_related = ("stock_item", "stock_item__supply_batch", "source_location", "destination_location")

    @admin.display(description="Histórico")
    def history_button(self, obj):
        url = f"/admin/stock/stockmovement/{obj.pk}/history/"
        return format_html(
            '<a href="{}" title="Ver histórico desta movimentação" '
            'style="color:#17a2b8;"><i class="fas fa-history"></i></a>',
            url
        )
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "notes":
            formfield.help_text = "✏️ Justifique aqui se alterou campos sensíveis (ex: quantidade, local, tipo de movimento)."
        return formfield

    @admin.display(description="Local")
    def location_display(self, obj):
        if obj.destination_location:
            return obj.destination_location.name
        elif obj.source_location:
            return obj.source_location.name
        return "—"

    @admin.display(description="Diferenças")
    def diff_display(self, obj):
        if not obj.prev_record:
            return "-"
        changes = []
        for field in ["quantity", "movement_type", "stock_item", "source_location", "destination_location"]:
            old = getattr(obj.prev_record, field, None)
            new = getattr(obj, field, None)
            if old != new:
                changes.append(f"{field}: {old} → {new}")
        return format_html("<br>".join(changes)) if changes else "–"
    
    def get_object(self, request, object_id, from_field=None):
        obj = super().get_object(request, object_id, from_field)
        if obj:
            try:
                obj.prev_record = obj.history.prev_record
            except Exception:
                obj.prev_record = None
        return obj

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("stock_item", "source_location", "destination_location")
        return qs

    def save_model(self, request, obj, form, change):
        if change:
            if hasattr(obj, "_history_user"):
                update_change_reason(obj, "Alteração manual no admin")
            obj._history_user = request.user
        super().save_model(request, obj, form, change)


    @admin.display(description="📌 Lote")
    def batch_code(self, obj):
        if obj.stock_item and obj.stock_item.supply_batch:
            return obj.stock_item.supply_batch.batch_code
        return "—"

    @admin.display(description="📦 Saldo Pós-Movimento")
    def post_movement_balance(self, obj):
        if obj.stock_item:
            return f"{obj.stock_item.quantity:.2f} {obj.stock_item.unit_of_measure}"
        return "—"

    @admin.display(description="📄 Resumo")
    def movement_summary(self, obj):
        return format_html(
            "<small>{} – {} – {}</small>",
            obj.get_movement_type_display(),
            obj.quantity,
            obj.date.strftime("%d/%m/%Y %H:%M")
        )
    @admin.display(description="Ajustado?")
    def was_adjusted(self, obj):
        if obj.history.count() > 1:
            # Obtem a entrada de histórico mais recente
            last_history = obj.history.first()
            user = getattr(last_history, "history_user", "—")
            dt = last_history.history_date.strftime("%d/%m/%Y %H:%M")
            reason = obj.adjustment_reason or "Motivo não informado"
            
            tooltip = f"Ajustado por {user} em {dt}: {reason}"
            return format_html(
                '<span title="{}" style="color:#ffc107; font-size: 16px;">✏️</span>',
                tooltip
            )
        return ""


    @admin.display(description="Tipo de movimento")
    def movement_type_badge(self, obj):
        cores = {
            "entrada":    ("#e2f0d9", "#155724"),  # verde suave
            "saida":      ("#f8d7da", "#721c24"),  # vermelho claro
            "ajuste":     ("#fff3cd", "#856404"),  # amarelo leve
            "transferencia": ("#d1ecf1", "#0c5460"),  # azul claro
            "insumo_producao": ("#ede7f6", "#4527a0"),  # roxo suave
            "producao_final": ("#e3f2fd", "#0d47a1"),  # azul escuro leve
        }

        icones = {
            "entrada": "⬅️",
            "saida": "➡️",
            "ajuste": "🔄",
            "transferencia": "🔁",
            "insumo_producao": "🍰",
            "producao_final": "✅",
        }

        bg_color, text_color = cores.get(obj.movement_type, ("#eeeeee", "#000"))
        label = obj.get_movement_type_display()
        icon = icones.get(obj.movement_type, "❔")

        history_user = getattr(obj.history.last(), "history_user", "—")
        tooltip = f"{label} por {history_user} em {obj.date:%d/%m/%Y %H:%M}"

        return format_html(
            '<span title="{}" style="background:{}; color:{}; padding:2px 8px; border-radius:6px;">{} {}</span>',
            tooltip, bg_color, text_color, icon, label
        )


    @admin.display(description="Estoque")
    def estoque_tooltip(self, obj):
        if obj.before_quantity is not None and obj.after_quantity is not None:
            return format_html(
                '<span title="Antes: {} / Depois: {}">{} → {}</span>',
                obj.before_quantity,
                obj.after_quantity,
                obj.before_quantity,
                obj.after_quantity
            )
        return "-"

    @admin.display(description="Usuário")
    def user_display(self, obj):
        history = obj.history.last()
        if history and history.history_user:
            return f"{history.history_user}"
        return "—"



# -------------------------------
# Admin: Locais de Estoque
# -------------------------------

@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


# -------------------------------
# Admin: Alerta de Estoque
# -------------------------------

@admin.register(StockThreshold)
class StockThresholdAdmin(admin.ModelAdmin):
    list_display = ("supply_item", "min_quantity", "alert_enabled")
    list_editable = ("min_quantity", "alert_enabled")
    search_fields = ("supply_item__name",)
