# stock/services/orchestrator.py

from decimal import Decimal
from django.db.models import Q
from stock.models import StockItem, StockLocation, StockMovement, StockMovementType
from supplies.models import SupplyBatch
from stock.models import StockAdjustmentReason 


class StockOrchestrator:
    @staticmethod
    def auto_add_to_stock(batch: SupplyBatch) -> bool:

        if not batch.is_active:
            return False

        if not batch or batch.stock_entry_created:
            return False

        if not batch.supply_item or not batch.supply_item.is_active:
            return False

        if batch.quantity <= Decimal("0.00"):
            return False

        default_location = StockLocation.objects.filter(is_active=True).first()
        if not default_location:
            return False

        exists = StockItem.objects.filter(
            supply_batch=batch,
            location=default_location
        ).exists()
        if exists:
            return False

        stock_item = StockItem.objects.create(
            supply_item=batch.supply_item,
            supply_batch=batch,
            location=default_location,
            quantity=batch.quantity,
            unit_of_measure=batch.supply_item.unit_of_measure
        )

        StockMovement.objects.create(
            stock_item=stock_item,
            movement_type=StockMovementType.INBOUND,
            quantity=batch.quantity,
            destination_location=default_location,
            reference=f"Lote {batch.batch_code}",
            notes="Entrada automática via StockOrchestrator"
        )

        # ✅ Marcar como lançado
        batch.stock_entry_created = True
        batch.save(update_fields=["stock_entry_created"])

        return True

    @staticmethod
    def force_entry(batch: SupplyBatch, location: StockLocation = None) -> bool:
        if not batch.is_active:
            return False

        location = location or StockLocation.objects.filter(is_active=True).first()
        if not location:
            return False
        

        # Verifica se já existe
        stock_item = StockItem.objects.filter(
            supply_batch=batch,
            location=location
        ).first()

        if stock_item:
            old_quantity = stock_item.quantity
            new_quantity = batch.quantity

            if old_quantity != new_quantity:
                diff = new_quantity - old_quantity
                stock_item.quantity = new_quantity
                stock_item.save(update_fields=["quantity"])

                StockMovement.objects.create(
                    stock_item=stock_item,
                    movement_type=StockMovementType.ADJUSTMENT,
                    quantity=abs(diff),
                    destination_location=location if diff > 0 else None,
                    source_location=location if diff < 0 else None,
                    adjustment_reason=StockAdjustmentReason.INVENTORY_ERROR,
                    reference=f"Ajuste do lote {batch.batch_code}",
                    notes=f"Ajuste manual de quantidade via admin: {old_quantity} → {new_quantity}"
                )

            # Atualiza flag mesmo sem alteração
            batch.stock_entry_created = True
            batch.save(update_fields=["stock_entry_created"])
            return True

        # Caso não exista, cria normalmente
        stock_item = StockItem.objects.create(
            supply_item=batch.supply_item,
            supply_batch=batch,
            location=location,
            quantity=batch.quantity,
            unit_of_measure=batch.supply_item.unit_of_measure
        )

        StockMovement.objects.create(
            stock_item=stock_item,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity=abs(diff),
            destination_location=location if diff > 0 else None,
            source_location=location if diff < 0 else None,
            adjustment_reason=StockAdjustmentReason.ADMIN_EDIT,  # 🔧 Usando o novo motivo
            reference=f"Ajuste do lote {batch.batch_code}",
            notes=f"Ajuste manual de quantidade via admin: {old_quantity} → {new_quantity}"
        )

        batch.stock_entry_created = True
        batch.save(update_fields=["stock_entry_created"])
        return True

