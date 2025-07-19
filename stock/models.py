import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords
from commons.enums import UnitOfMeasureEnum
from supplies.models import SupplyItem, SupplyBatch
from functools import cached_property


# -------------------------------
# Localização física do estoque
# -------------------------------
class StockLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Nome", max_length=100)
    description = models.TextField("Descrição", blank=True)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Local de Estoque"
        verbose_name_plural = "Locais de Estoque"

    def __str__(self):
        return self.name


# ---------------------------------------
# Item armazenado (vinculado a lote)
# ---------------------------------------
class StockItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    supply_item = models.ForeignKey(
        SupplyItem,
        on_delete=models.CASCADE,
        verbose_name="Item de Insumo",
        related_name="stock_items",
        null=True,
        blank=True,
    )

    supply_batch = models.ForeignKey(
        SupplyBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Lote de Insumo",
        related_name="stock_items"
    )

    location = models.ForeignKey(
        StockLocation,
        on_delete=models.CASCADE,
        related_name="stock_items",
        verbose_name="Local de Armazenamento"
    )

    quantity = models.DecimalField("Quantidade Atual", max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField("Unidade", max_length=16, choices=UnitOfMeasureEnum.choices)

    production_batch = models.ForeignKey(
        "production.ProductionBatch",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Lote de Produção"
    )

    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Estoque"
        verbose_name_plural = "Estoques"
        unique_together = ("supply_batch", "location")  # 🔐 garante que não haja duplicidade de lote em local
        ordering = ["supply_item__name", "supply_batch__expiration_date"]


    # ----------- Propriedades auxiliares -----------

    @property
    def batch_code(self):
        return self.supply_batch.batch_code if self.supply_batch else ""

    @property
    def expiration_date(self):
        return self.supply_batch.expiration_date if self.supply_batch else None

    @property
    def is_expired(self):
        return self.expiration_date and self.expiration_date < timezone.now().date()

    @property
    def is_expiring_soon(self):
        return self.expiration_date and 0 <= self.days_to_expire <= 7

    @property
    def days_to_expire(self):
        if not self.expiration_date:
            return None
        return (self.expiration_date - timezone.now().date()).days

    @property
    def total_movements(self):
        return self.movements.count()

    @property
    def last_movement_date(self):
        last = self.movements.order_by("-date").first()
        return last.date if last else None

    @property
    def total_in(self):
        return self.movements.filter(
            movement_type__in=[
                StockMovementType.INBOUND, StockMovementType.PRODUCTION_OUTPUT
            ]
        ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0.00")

    @property
    def total_out(self):
        return self.movements.filter(
            movement_type__in=[
                StockMovementType.OUTBOUND, StockMovementType.PRODUCTION_INPUT
            ]
        ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0.00")

    @property
    def average_daily_usage(self):
        recent_outs = self.movements.filter(
            movement_type__in=[
                StockMovementType.OUTBOUND, StockMovementType.PRODUCTION_INPUT
            ],
            date__gte=timezone.now() - timezone.timedelta(days=30)
        )
        total_used = sum(m.quantity for m in recent_outs)
        return total_used / Decimal("30.0") if total_used else Decimal("0.00")

    @property
    def estimated_days_remaining(self):
        avg = self.average_daily_usage
        return int(self.quantity / avg) if avg > 0 else None

    @property
    def stock_status(self):
        if self.is_expired:
            return "VENCIDO"
        elif self.is_expiring_soon:
            return "EXPIRANDO"
        elif self.quantity <= 0:
            return "EM FALTA"
        elif self.is_low_stock:
            return "EM ALERTA"
        return "OK"

    @property
    def is_low_stock(self):
        threshold = getattr(self, "threshold", None)
        if threshold and threshold.alert_enabled:
            return self.quantity < threshold.min_quantity
        return self.quantity < Decimal("5.0")  # fallback padrão

    def recalculate_stock(self):
        self.quantity = self.total_in - self.total_out
        self.save()
    
    @cached_property
    def resolved_supply_item(self):
        """Fallback inteligente para obter supply_item via supply_batch se não estiver definido diretamente."""
        return self.supply_item or (self.supply_batch.supply_item if self.supply_batch else None)

    @cached_property
    def effective_unit(self):
        """Unidade de medida resolvida: campo direto ou herdado do item de insumo."""
        return self.unit_of_measure or (
            self.supply_item.unit_of_measure if self.supply_item else None
        )

    @cached_property
    def object_name(self):
        """Nome amigável do item para uso em exibições e logs."""
        item = self.resolved_supply_item
        return item.name if item else "-"

    def __str__(self):
        return f"{self.object_name} | {self.batch_code} | {self.quantity} {self.effective_unit} @ {self.location}"




# -------------------------
# Tipos de movimentação
# -------------------------
class StockMovementType(models.TextChoices):
    INBOUND = "entrada", "Entrada"
    OUTBOUND = "saida", "Saída"
    TRANSFER = "transferencia", "Transferência"
    ADJUSTMENT = "ajuste", "Ajuste"
    PRODUCTION_INPUT = "insumo_producao", "Produção"
    PRODUCTION_OUTPUT = "producao_final", "Produto Acabado"


# -------------------------
# Motivo de Ajuste
# -------------------------
class StockAdjustmentReason(models.TextChoices):
    INVENTORY_ERROR = "erro_inventario", "Erro de Inventário"
    DAMAGE = "avaria", "Avaria"
    THEFT = "furto", "Furto"
    SAMPLE = "amostra", "Amostra Técnica"
    ADMIN_EDIT = "ajuste_admin", "Ajuste Manual via Admin"
    OTHER = "outro", "Outro"

from django.core.exceptions import ValidationError

class StockMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField("Tipo de movimento", max_length=32, choices=StockMovementType.choices)
    quantity = models.DecimalField("Quantidade", max_digits=10, decimal_places=2)
    date = models.DateTimeField("Data", default=timezone.now)
    adjustment_reason = models.CharField("Motivo de ajuste", max_length=32, choices=StockAdjustmentReason.choices, blank=True, null=True)

    source_location = models.ForeignKey(
        StockLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_movements"
    )
    destination_location = models.ForeignKey(
        StockLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="destination_movements"
    )

    reference = models.CharField("Referência externa", max_length=100, blank=True)
    notes = models.TextField("Observações", blank=True)

    production_order = models.ForeignKey(
        "production.ProductionOrder",
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Ordem de Produção Relacionada"
    )

    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    history = HistoricalRecords()
    before_quantity = models.DecimalField("Estoque Antes", max_digits=10, decimal_places=2, null=True, blank=True)
    after_quantity = models.DecimalField("Estoque Depois", max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_movement_type_display()} de {self.quantity} {self.stock_item.unit_of_measure} - {self.stock_item.object_name}"

    # ---------------------------
    # Validações e Propriedades
    # ---------------------------

    @property
    def is_inbound(self):
        return self.movement_type in [
            StockMovementType.INBOUND,
            StockMovementType.PRODUCTION_OUTPUT
        ]

    @property
    def is_outbound(self):
        return self.movement_type in [
            StockMovementType.OUTBOUND,
            StockMovementType.PRODUCTION_INPUT,
            StockMovementType.TRANSFER
        ]

    def clean(self):
        super().clean()
        if self.is_outbound and self.stock_item:
            available_qty = self.stock_item.quantity
            if self.quantity > available_qty:
                raise ValidationError({
                    "quantity": (
                        f"Quantidade de saída ({self.quantity}) "
                        f"excede o estoque disponível ({available_qty})."
                    )
                })

    def save(self, *args, **kwargs):
        if not self.pk and self.stock_item:  # somente no create
            self.before_quantity = self.stock_item.quantity
        super().save(*args, **kwargs)
        if self.stock_item:
            self.after_quantity = self.stock_item.quantity
            StockMovement.objects.filter(pk=self.pk).update(after_quantity=self.after_quantity)


    @property
    def location_display(self):
        if self.source_location and self.destination_location:
            return f"{self.source_location.name} → {self.destination_location.name}"
        elif self.source_location:
            return f"{self.source_location.name} → [Saída]"
        elif self.destination_location:
            return f"[Entrada] → {self.destination_location.name}"
        return "-"

    @property
    def movement_summary(self):
        return f"{self.date.date()} | {self.get_movement_type_display()} | {self.quantity} | Estoque atual: {self.stock_item.quantity}"



# ----------------------------------
# Alerta mínimo de estoque
# ----------------------------------
class StockThreshold(models.Model):
    supply_item = models.OneToOneField(
        SupplyItem,
        on_delete=models.CASCADE,
        related_name="threshold",
        verbose_name="Item de Insumo",
        null=True,
        blank=True,
    )
    min_quantity = models.DecimalField("Quantidade mínima", max_digits=10, decimal_places=2)
    alert_enabled = models.BooleanField("Alerta Ativo", default=True)

    class Meta:
        verbose_name = "Alerta de Estoque"
        verbose_name_plural = "Alertas de Estoque"

    def __str__(self):
        return f"Alerta para {self.supply_item.name} ({self.min_quantity})"
