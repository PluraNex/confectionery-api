import uuid
from django.db import models
from django.template.defaultfilters import slugify
from django.core.validators import MinValueValidator




class CakeSizeType(models.TextChoices):
    SMALL = "pequeno", "Pequeno"
    MEDIUM = "medio", "Médio"
    LARGE = "grande", "Grande"

# -------------------------
# Categorias de bolo
# -------------------------
class CakeCategory(models.TextChoices):
    CHOCOLATE = 'chocolate', 'Bolos de Chocolate'
    BRANCOS = 'brancos', 'Bolos Brancos'
    ZERO_ACUCAR = 'zero_acucar', 'Bolos Zero Açúcar'
    CASEIROS = 'caseiros', 'Bolos Caseiros'
    CASAMENTO = 'casamento', 'Bolos de Casamento'
    ANIVERSARIO = 'aniversario', 'Bolos de Aniversário'
    INFANTIL = 'infantil', 'Bolos Infantis'
    TEMATICOS = 'tematicos', 'Bolos Temáticos'
    GOURMET = 'gourmet', 'Bolos Gourmet'
    NAKED_CAKE = 'naked_cake', 'Naked Cakes'
    RED_VELVET = 'red_velvet', 'Red Velvet'
    KIT_FESTA = 'kit_festa', 'Kit Festa'
    OUTROS = 'outros', 'Outros'

# -------------------------
# Entidade Principal: Cake
# -------------------------
class Cake(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Nome", max_length=100)
    description = models.TextField("Descrição")
    category = models.CharField("Categoria", max_length=20, choices=CakeCategory.choices)
    customizable = models.BooleanField("Personalizável", default=False)
    estimated_weight_kg = models.DecimalField("Peso estimado (kg)", max_digits=5, decimal_places=2, null=True, blank=True)
    is_available_for_delivery = models.BooleanField("Disponível para entrega", default=True)
    is_available_for_pickup = models.BooleanField("Disponível para retirada", default=True)
    production_time_days = models.PositiveIntegerField("Tempo de produção (dias)", default=1)
    is_active = models.BooleanField("Ativo", default=True)
    internal_notes = models.TextField("Notas internas", null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# -------------------------
# Composição
# -------------------------
class CakeComposition(models.Model):
    cake = models.OneToOneField(Cake, on_delete=models.CASCADE, related_name='composition')
    topping = models.CharField("Cobertura", max_length=100)

    def __str__(self):
        return f"Composição de {self.cake.name}"

class CakeFlavor(models.Model):
    FLAVOR_TYPES = [
        ("massa", "Massa"),
        ("recheio", "Recheio"),
        ("cobertura", "Cobertura"),
    ]
    composition = models.ForeignKey(CakeComposition, on_delete=models.CASCADE, related_name="flavors")
    type = models.CharField("Tipo", max_length=20, choices=FLAVOR_TYPES)
    description = models.CharField("Descrição", max_length=100)

    def __str__(self):
        return f"{self.get_type_display()}: {self.description}"

class CakeIngredient(models.Model):
    composition = models.ForeignKey(CakeComposition, on_delete=models.CASCADE, related_name="ingredients")
    name = models.CharField("Ingrediente", max_length=50)
    description = models.CharField("Descrição", max_length=100)

    def __str__(self):
        return f"{self.name}: {self.description}"

class CakeAllergen(models.Model):
    composition = models.ForeignKey(CakeComposition, on_delete=models.CASCADE, related_name="allergens")
    name = models.CharField("Alergênico", max_length=50, choices=[
        ("gluten", "Glúten"),
        ("lactose", "Lactose"),
        ("castanhas", "Castanhas"),
        ("ovos", "Ovos"),
        ("soja", "Soja"),
    ])
    present = models.BooleanField("Presente")

    def __str__(self):
        return f"{self.name} - {'Sim' if self.present else 'Não'}"

# -------------------------
# Tamanhos disponíveis (sem preço)
# -------------------------
class CakeSize(models.Model):
    cake = models.ForeignKey("Cake", on_delete=models.CASCADE, related_name="sizes")
    description = models.CharField(
        max_length=20,
        choices=CakeSizeType.choices,
        default=CakeSizeType.MEDIUM,
        verbose_name="Tamanho"
    )
    serves = models.PositiveIntegerField(verbose_name="Serve (pessoas)")


# -------------------------
# Imagens
# -------------------------
class ImageType(models.TextChoices):
    PRINCIPAL = 'principal', 'Principal'
    GALERIA = 'galeria', 'Galeria'
    DETALHE = 'detalhe', 'Detalhe'

class CakeImage(models.Model):
    cake = models.ForeignKey("Cake", on_delete=models.CASCADE, related_name='images')
    image = models.ImageField("Imagem", upload_to="cakes/", null=True, blank=True)
    image_type = models.CharField("Tipo", max_length=20, choices=ImageType.choices)
    is_cover = models.BooleanField("Imagem de capa", default=False)

    def __str__(self):
        tipo = self.get_image_type_display()
        return f"{tipo} - {self.cake.name}" + (" [CAPA]" if self.is_cover else "")

# -------------------------
# Informações nutricionais
# -------------------------
class NutritionalInfo(models.Model):
    cake = models.OneToOneField(Cake, on_delete=models.CASCADE, related_name='nutritional_info')
    portion_description = models.CharField("Descrição da porção", max_length=100, default="Porção de 100g (1 fatia)")
    energy_kcal = models.PositiveIntegerField("Valor energético (kcal)")
    energy_kj = models.PositiveIntegerField("Valor energético (kJ)")
    carbohydrates_g = models.DecimalField("Carboidratos (g)", max_digits=5, decimal_places=2)
    proteins_g = models.DecimalField("Proteínas (g)", max_digits=5, decimal_places=2)
    total_fats_g = models.DecimalField("Gorduras totais (g)", max_digits=5, decimal_places=2)
    saturated_fats_g = models.DecimalField("Gorduras saturadas (g)", max_digits=5, decimal_places=2)
    trans_fats_g = models.DecimalField("Gorduras trans (g)", max_digits=5, decimal_places=2)
    fiber_g = models.DecimalField("Fibra alimentar (g)", max_digits=5, decimal_places=2)
    sodium_mg = models.PositiveIntegerField("Sódio (mg)")
    vd_energy = models.PositiveIntegerField("VD% Energia", default=0)
    vd_carbohydrates = models.PositiveIntegerField("VD% Carboidratos", default=0)
    vd_proteins = models.PositiveIntegerField("VD% Proteínas", default=0)
    vd_total_fats = models.PositiveIntegerField("VD% Gorduras totais", default=0)
    vd_saturated_fats = models.PositiveIntegerField("VD% Gorduras saturadas", default=0)
    vd_fiber = models.PositiveIntegerField("VD% Fibra alimentar", default=0)
    vd_sodium = models.PositiveIntegerField("VD% Sódio", default=0)

    def __str__(self):
        return f"Info Nutricional de {self.cake.name}"
