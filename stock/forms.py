from django import forms
from django.core.exceptions import ValidationError
from stock.models import StockMovement, StockMovementType, StockItem


class StockMovementAdminForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")

        # 🔹 Ajuda dinâmica com estoque atual
        if instance and instance.stock_item:
            estoque = instance.stock_item.quantity
            unidade = instance.stock_item.unit_of_measure
            self.fields["quantity"].help_text = f"Estoque atual: {estoque} {unidade}"

        elif "stock_item" in self.data:
            try:
                stock_item_id = self.data.get("stock_item")
                stock_item = StockItem.objects.get(id=stock_item_id)
                estoque = stock_item.quantity
                unidade = stock_item.unit_of_measure
                self.fields["quantity"].help_text = f"Estoque atual: {estoque} {unidade}"
            except StockItem.DoesNotExist:
                pass

        # 🛈 Ajuda contextual para o usuário
        self.fields["quantity"].help_text = self.fields["quantity"].help_text or "Informe uma quantidade positiva."
        self.fields["adjustment_reason"].help_text = "Obrigatório somente para ajustes manuais."
        self.fields["source_location"].help_text = "Obrigatório em saídas e transferências."
        self.fields["destination_location"].help_text = "Obrigatório em entradas e transferências."
        self.fields["notes"].help_text = "Se estiver editando e alterar algum campo, justifique aqui."

    def clean(self):
        cleaned_data = super().clean()
        stock_item = cleaned_data.get("stock_item")
        movement_type = cleaned_data.get("movement_type")
        quantity = cleaned_data.get("quantity")
        notes = cleaned_data.get("notes")
        adjustment_reason = cleaned_data.get("adjustment_reason")
        source_location = cleaned_data.get("source_location")
        destination_location = cleaned_data.get("destination_location")

        # -------------------------------
        # ❌ 1. Bloqueia saídas acima do estoque atual
        # -------------------------------
        if stock_item and movement_type in [
            StockMovementType.OUTBOUND,
            StockMovementType.PRODUCTION_INPUT,
            StockMovementType.TRANSFER
        ]:
            available = stock_item.quantity
            if quantity and quantity > available:
                raise ValidationError({
                    "quantity": f"❌ A quantidade ({quantity}) excede o estoque disponível ({available})."
                })

        # -------------------------------
        # ❌ 2. Quantidade não pode ser 0 ou negativa
        # -------------------------------
        if quantity is not None and quantity <= 0:
            raise ValidationError({
                "quantity": "❌ A quantidade deve ser maior que zero."
            })

        # -------------------------------
        # ⚠️ 3. Motivo de ajuste obrigatório para ajustes manuais
        # -------------------------------
        if movement_type == StockMovementType.ADJUSTMENT and not adjustment_reason:
            raise ValidationError({
                "adjustment_reason": "⚠️ Para ajustes, selecione o motivo do ajuste."
            })

        # -------------------------------
        # ⚠️ 4. Source location obrigatório em saídas/transferências
        # -------------------------------
        if movement_type in [StockMovementType.OUTBOUND, StockMovementType.TRANSFER] and not source_location:
            raise ValidationError({
                "source_location": "⚠️ Campo obrigatório para esse tipo de movimentação."
            })

        # -------------------------------
        # ⚠️ 5. Destination location obrigatório em entradas/transferências
        # -------------------------------
        if movement_type in [StockMovementType.INBOUND, StockMovementType.TRANSFER] and not destination_location:
            raise ValidationError({
                "destination_location": "⚠️ Campo obrigatório para esse tipo de movimentação."
            })

        # -------------------------------
        # ✏️ 6. Justificativa obrigatória se houve edição crítica
        # -------------------------------
        if self.instance.pk:
            campos_criticos = {
                "quantity", "movement_type", "stock_item",
                "source_location", "destination_location"
            }

            alterados = set(self.changed_data)
            if campos_criticos.intersection(alterados):
                if not notes:
                    raise ValidationError({
                        "notes": "⚠️ Por favor, justifique a alteração no campo 'Observações'."
                    })

        return cleaned_data
