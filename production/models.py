import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


# --------------------------
# ENUMS
# --------------------------
class ProductionOrderStatus(models.TextChoices):
    PLANNED = "planejada", "Planejada"
    IN_PROGRESS = "em_execucao", "Em execução"
    COMPLETED = "concluida", "Concluída"
    CANCELLED = "cancelada", "Cancelada"


class ProductionStepType(models.TextChoices):
    PREPARE_MASS = "massa", "Preparar Massa"
    BAKE = "assar", "Assar"
    FILL = "rechear", "Rechear"
    COVER = "cobrir", "Cobrir/Decorar"
    PACKAGE = "embalar", "Embalar"
    OTHER = "outro", "Outro"


# --------------------------
# ORDEM DE PRODUÇÃO
# --------------------------
class ProductionOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cake = models.ForeignKey("cakes.Cake", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField("Quantidade a produzir")
    scheduled_date = models.DateField("Data programada")
    status = models.CharField("Status", max_length=32, choices=ProductionOrderStatus.choices, default=ProductionOrderStatus.PLANNED)

    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Responsável"
    )

    started_at = models.DateTimeField("Início da produção", null=True, blank=True)
    finished_at = models.DateTimeField("Conclusão da produção", null=True, blank=True)

    produced_quantity = models.PositiveIntegerField("Quantidade produzida", null=True, blank=True)
    waste_quantity = models.PositiveIntegerField("Perda", null=True, blank=True)
    rework_quantity = models.PositiveIntegerField("Retrabalho", null=True, blank=True)

    notes = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Ordem de Produção"
        verbose_name_plural = "Ordens de Produção"
        ordering = ["-scheduled_date"]

    def __str__(self):
        return f"{self.cake.name} x{self.quantity} - {self.scheduled_date} ({self.get_status_display()})"

    # --------- Propriedades estratégicas ---------
    @property
    def is_overdue(self):
        return self.status in [ProductionOrderStatus.PLANNED, ProductionOrderStatus.IN_PROGRESS] and self.scheduled_date < timezone.now().date()

    @property
    def is_today(self):
        return self.scheduled_date == timezone.now().date()

    @property
    def is_completed(self):
        return self.status == ProductionOrderStatus.COMPLETED

    @property
    def is_delayed(self):
        return not self.is_completed and self.scheduled_date < timezone.now().date()

    @property
    def has_started(self):
        return self.started_at is not None

    @property
    def is_active(self):
        return self.status == ProductionOrderStatus.IN_PROGRESS

    @property
    def production_duration_minutes(self):
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds() / 60)
        return None

    @property
    def yield_percentage(self):
        if not self.quantity:
            return None
        return round((self.produced_quantity or 0) / self.quantity * 100, 2)

    @property
    def progress_percentage(self):
        if not self.quantity:
            return 0
        return min(round((self.produced_quantity or 0) / self.quantity * 100, 2), 100)

    @property
    def total_steps(self):
        return self.steps.count()

    @property
    def completed_steps(self):
        return self.steps.filter(is_completed=True).count()

    @property
    def steps_progress_percentage(self):
        if self.total_steps == 0:
            return 0
        return round(self.completed_steps / self.total_steps * 100, 2)

    @property
    def has_batches(self):
        return self.batches.exists()


# --------------------------
# ETAPA DA PRODUÇÃO
# --------------------------
class ProductionStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name="steps")
    step_type = models.CharField("Etapa", max_length=32, choices=ProductionStepType.choices)
    description = models.TextField("Descrição", blank=True)

    started_at = models.DateTimeField("Início", null=True, blank=True)
    finished_at = models.DateTimeField("Conclusão", null=True, blank=True)
    duration_minutes = models.PositiveIntegerField("Duração (min)", null=True, blank=True)

    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Responsável"
    )

    is_completed = models.BooleanField("Concluída", default=False)

    class Meta:
        verbose_name = "Etapa da Produção"
        verbose_name_plural = "Etapas da Produção"
        ordering = ["step_type", "started_at"]

    def __str__(self):
        return f"{self.get_step_type_display()} ({self.order})"

    def save(self, *args, **kwargs):
        if self.started_at and self.finished_at and not self.duration_minutes:
            delta = self.finished_at - self.started_at
            self.duration_minutes = int(delta.total_seconds() / 60)
        super().save(*args, **kwargs)

    # --------- Propriedades auxiliares ---------
    @property
    def is_late(self):
        return not self.is_completed and self.started_at and self.started_at.date() < timezone.now().date()

    @property
    def status_label(self):
        if self.is_completed:
            return "Concluída"
        elif self.started_at:
            return "Em Execução"
        return "Pendente"


# --------------------------
# EXECUÇÃO FÍSICA (Batch)
# --------------------------
class ProductionBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name="batches")
    batch_code = models.CharField("Código do lote", max_length=50)
    produced_quantity = models.PositiveIntegerField("Quantidade produzida", default=0)

    started_at = models.DateTimeField("Início", auto_now_add=True)
    finished_at = models.DateTimeField("Conclusão", null=True, blank=True)

    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Responsável"
    )

    notes = models.TextField("Observações", blank=True)

    class Meta:
        verbose_name = "Lote de Produção"
        verbose_name_plural = "Lotes de Produção"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Lote {self.batch_code} - {self.order}"

    # --------- Propriedades auxiliares ---------
    @property
    def duration_minutes(self):
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_open(self):
        return self.finished_at is None
