from rest_framework import serializers
from supplies.models import SupplyItem, SupplyBatch, SupplyNutritionInfo, SupplyIngredientDetail, SupplyProductTag
from commons import UnitOfMeasureEnum, get_unit_description



class SupplyNutritionInfoSerializer(serializers.ModelSerializer):
    calories_kcal = serializers.SerializerMethodField(read_only=True)
    sodium_mg = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplyNutritionInfo
        fields = [
            "serving_size",
            "calories", "calories_kcal",
            "protein",
            "fat", "saturated_fat", "trans_fat",
            "carbohydrates", "sugars", "fiber",
            "sodium", "sodium_mg",
            "created_at",
        ]

    # ---------------------
    # Métodos auxiliares
    # ---------------------

    def get_calories_kcal(self, obj):
        """Retorna calorias formatadas com unidade."""
        return f"{obj.calories} kcal" if obj.calories is not None else None

    def get_sodium_mg(self, obj):
        """Retorna sódio com sufixo."""
        return f"{obj.sodium} mg" if obj.sodium is not None else None

    def validate(self, data):
        """Validação cruzada para garantir consistência dos dados."""
        if data.get("trans_fat") and data.get("trans_fat") > data.get("fat", 0):
            raise serializers.ValidationError({
                "trans_fat": "Gordura trans não pode ser maior que a gordura total."
            })
        return data


class SupplyIngredientDetailSerializer(serializers.ModelSerializer):
    gluten_status = serializers.SerializerMethodField(read_only=True)
    vegan_status = serializers.SerializerMethodField(read_only=True)
    has_warnings = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplyIngredientDetail
        fields = [
            "ingredient_list",
            "contains_gluten", "gluten_status",
            "is_vegan", "vegan_status",
            "warnings", "has_warnings",
            "created_at"
        ]

    # ---------------------
    # Métodos auxiliares
    # ---------------------

    def get_gluten_status(self, obj):
        """Retorna texto amigável sobre glúten."""
        return "Contém glúten" if obj.contains_gluten else "Não contém glúten"

    def get_vegan_status(self, obj):
        """Retorna texto amigável sobre veganismo."""
        return "Vegano" if obj.is_vegan else "Não vegano"

    def get_has_warnings(self, obj):
        """Retorna se há advertências registradas."""
        return bool(obj.warnings and obj.warnings.strip())

    def validate(self, data):
        """Valida lógica cruzada, se necessário."""
        ingredients = data.get("ingredient_list", "")
        if "ovo" in ingredients.lower() and data.get("is_vegan", False):
            raise serializers.ValidationError({
                "is_vegan": "Item contém ovo e não pode ser marcado como vegano."
            })
        return data

class SupplyProductTagSerializer(serializers.ModelSerializer):
    tag_type_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplyProductTag
        fields = ["id", "name", "tag_type", "tag_type_display"]

    def get_tag_type_display(self, obj):
        return obj.get_tag_type_display()

class SupplyBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplyBatch
        fields = [
            "id", "batch_code", "expiration_date",
            "quantity", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class SupplyItemSerializer(serializers.ModelSerializer):
    unit_of_measure_display = serializers.SerializerMethodField()
    unit_description = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()
    category_purpose = serializers.SerializerMethodField()
    nutrition_info = SupplyNutritionInfoSerializer(read_only=True)
    ingredient_detail = SupplyIngredientDetailSerializer(read_only=True)
    batches = SupplyBatchSerializer(many=True, read_only=True)
    tags = SupplyProductTagSerializer(many=True, read_only=True)

    class Meta:
        model = SupplyItem
        fields = [
            "id", "sku", "name", "description", "image", "barcode",
            "unit_of_measure", "unit_of_measure_display", "unit_description",
            "category", "category_display", "category_purpose",
            "origin_country", "expiration_control", "batch_control",
            "regulatory_code", "is_ingredient", "tags",
            "nutrition_info", "ingredient_detail",
            "is_active", "created_at", "updated_at", "batches"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_category_display(self, obj):
        return obj.get_category_display()

    def get_category_purpose(self, obj):
        return obj.category_purpose

    def get_unit_of_measure_display(self, obj):
        return obj.get_unit_of_measure_display()

    def get_unit_description(self, obj):
        return get_unit_description(obj.unit_of_measure)

    def validate_unit_of_measure(self, value):
        if value not in UnitOfMeasureEnum.values:
            raise serializers.ValidationError(f"'{value}' não é uma unidade válida.")
        return value

    def validate_sku(self, value):
        value = value.strip().upper().replace(" ", "")
        if not value.isalnum():
            raise serializers.ValidationError("O SKU deve conter apenas letras e números.")
        return value

class BulkSupplyItemWithBatchSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        created_items = []
        for item_data in validated_data:
            serializer = self.child.__class__(data=item_data, context=self.context)
            serializer.is_valid(raise_exception=True)
            created_items.append(serializer.save())
        return created_items


class SupplyItemWithBatchSerializer(serializers.Serializer):
    supply_item = SupplyItemSerializer()
    supply_batch = SupplyBatchSerializer(required=False)

    def create(self, validated_data):
        supply_item_data = validated_data["supply_item"]
        supply_batch_data = validated_data.get("supply_batch")

        item_serializer = SupplyItemSerializer(data=supply_item_data, context=self.context)
        item_serializer.is_valid(raise_exception=True)
        item = item_serializer.save()

        if item.batch_control:
            if not supply_batch_data:
                raise serializers.ValidationError({
                    "supply_batch": "Lote é obrigatório para itens com controle de lote."
                })
            SupplyBatch.objects.create(supply_item=item, **supply_batch_data)

        return item

    class Meta:
        list_serializer_class = BulkSupplyItemWithBatchSerializer





