from rest_framework import serializers
from .models import (
    Cake,
    CakeComposition,
    CakeFlavor,
    CakeIngredient,
    CakeAllergen,
    CakeSize,
    CakeImage,
    NutritionalInfo,
    ImageType,
)


class CakeFlavorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CakeFlavor
        fields = ['id', 'type', 'description']


class CakeIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = CakeIngredient
        fields = ['id', 'name', 'description']


class CakeAllergenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CakeAllergen
        fields = ['id', 'name', 'present']


class CakeCompositionSerializer(serializers.ModelSerializer):
    flavors = CakeFlavorSerializer(many=True)
    ingredients = CakeIngredientSerializer(many=True)
    allergens = CakeAllergenSerializer(many=True)

    class Meta:
        model = CakeComposition
        fields = ['id', 'topping', 'flavors', 'ingredients', 'allergens']


class CakeSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CakeSize
        fields = ['id', 'description', 'serves']


class CakeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CakeImage
        fields = ['id', 'url', 'image_type']


class NutritionalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionalInfo
        fields = [
            "portion_description",
            "energy_kcal", "energy_kj",
            "carbohydrates_g", "proteins_g", "total_fats_g",
            "saturated_fats_g", "trans_fats_g", "fiber_g", "sodium_mg",
            "vd_energy", "vd_carbohydrates", "vd_proteins", "vd_total_fats",
            "vd_saturated_fats", "vd_fiber", "vd_sodium"
        ]

class CakeSerializer(serializers.ModelSerializer):
    composition = CakeCompositionSerializer()
    sizes = CakeSizeSerializer(many=True)
    images = CakeImageSerializer(many=True)
    nutritional_info = NutritionalInfoSerializer(required=False)

    class Meta:
        model = Cake
        fields = [
            'id', 'name', 'description', 'category',
            'customizable', 'estimated_weight_kg',
            'is_available_for_delivery', 'is_available_for_pickup',
            'production_time_days', 'is_active', 'internal_notes',
            'slug', 'created_at', 'updated_at',
            'composition', 'sizes', 'images', 'nutritional_info',
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def create(self, validated_data):
        composition_data = validated_data.pop('composition')
        flavors = composition_data.pop('flavors')
        ingredients = composition_data.pop('ingredients')
        allergens = composition_data.pop('allergens')

        sizes_data = validated_data.pop('sizes')
        images_data = validated_data.pop('images')
        nutritional_data = validated_data.pop('nutritional_info', None)

        cake = Cake.objects.create(**validated_data)

        composition = CakeComposition.objects.create(cake=cake, **composition_data)

        for f in flavors:
            CakeFlavor.objects.create(composition=composition, **f)
        for i in ingredients:
            CakeIngredient.objects.create(composition=composition, **i)
        for a in allergens:
            CakeAllergen.objects.create(composition=composition, **a)

        for size in sizes_data:
            CakeSize.objects.create(cake=cake, **size)

        for image in images_data:
            CakeImage.objects.create(cake=cake, **image)

        if nutritional_data:
            NutritionalInfo.objects.create(cake=cake, **nutritional_data)

        return cake

    def update(self, instance, validated_data):
        composition_data = validated_data.pop('composition', None)
        sizes_data = validated_data.pop('sizes', None)
        images_data = validated_data.pop('images', None)
        nutritional_data = validated_data.pop('nutritional_info', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Atualiza composição
        if composition_data:
            flavors = composition_data.pop('flavors', [])
            ingredients = composition_data.pop('ingredients', [])
            allergens = composition_data.pop('allergens', [])

            composition, _ = CakeComposition.objects.update_or_create(
                cake=instance,
                defaults=composition_data
            )

            composition.flavors.all().delete()
            composition.ingredients.all().delete()
            composition.allergens.all().delete()

            for f in flavors:
                CakeFlavor.objects.create(composition=composition, **f)
            for i in ingredients:
                CakeIngredient.objects.create(composition=composition, **i)
            for a in allergens:
                CakeAllergen.objects.create(composition=composition, **a)

        if sizes_data is not None:
            instance.sizes.all().delete()
            for size in sizes_data:
                CakeSize.objects.create(cake=instance, **size)

        if images_data is not None:
            instance.images.all().delete()
            for image in images_data:
                CakeImage.objects.create(cake=instance, **image)

        if nutritional_data:
            NutritionalInfo.objects.update_or_create(
                cake=instance,
                defaults=nutritional_data
            )

        return instance
