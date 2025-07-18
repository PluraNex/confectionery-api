import uuid
from django.db import models
from commons.enums import UnitOfMeasureEnum, get_unit_description
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models.functions import Now

# ------------------------------
# Categorias de Suprimentos
# ------------------------------
class SupplyCategory(models.TextChoices):
    BASE = "base", "Base do Bolo"
    FILLING = "filling", "Recheio"
    TOPPING = "topping", "Cobertura"
    FLAVORING = "flavoring", "Aromatizante"
    COLORING = "coloring", "Corante"
    DECORATION = "decoration", "Decoração"
    GARNISH = "garnish", "Enfeite Comestível"
    MOLD = "mold", "Forma / Molde"
    PACKAGING = "packaging", "Embalagem"
    LABEL = "label", "Etiqueta"
    STICKER = "sticker", "Adesivo"
    CLEANING = "cleaning", "Produto de Limpeza"
    EPI = "epi", "Equipamento de Proteção"
    UTENSIL = "utensil", "Utensílio"
    TOOL = "tool", "Ferramenta Técnica"
    RAW_MATERIAL = "raw_material", "Matéria-prima Diversa"
    ADDITIVE = "additive", "Aditivo"
    PROMO_ITEM = "promo_item", "Item Promocional"
    OTHER = "other", "Outro"

    @classmethod
    def help_text(cls, value: str) -> str:
        return {
            cls.BASE: "Ingredientes principais (farinha, ovos, leite)",
            cls.FILLING: "Recheios prontos ou compostos para camadas",
            cls.TOPPING: "Coberturas (chocolate, chantilly, ganache etc.)",
            cls.FLAVORING: "Essências e extratos (baunilha, rum, limão, etc.)",
            cls.COLORING: "Corantes alimentícios (gel, pó, líquido)",
            cls.DECORATION: "Pérolas, glitter comestível, papel arroz, flores artificiais",
            cls.GARNISH: "Frutas secas, castanhas, confeitos — acabamento final",
            cls.MOLD: "Formas, moldes de silicone, bases acrílicas",
            cls.PACKAGING: "Caixas, potes, plásticos, bandejas",
            cls.LABEL: "Etiquetas de validade, QR Code, código de barras",
            cls.STICKER: "Adesivos de marca, lacres, decorativos",
            cls.CLEANING: "Sabão neutro, álcool, desinfetante, papel-toalha",
            cls.EPI: "Toucas, luvas, aventais — segurança alimentar",
            cls.UTENSIL: "Espátulas, batedores, colheres, balanças",
            cls.TOOL: "Termômetros, cronômetros, aerógrafos",
            cls.RAW_MATERIAL: "Emulsificantes, estabilizantes, insumos técnicos",
            cls.ADDITIVE: "Conservantes, espessantes, enzimas",
            cls.PROMO_ITEM: "Brindes, cartões, folders, fitilhos",
            cls.OTHER: "Categoria temporária — use com cautela",
        }.get(value, "")

# Define categorias permitidas como ingredientes
INGREDIENT_CATEGORIES = {
    SupplyCategory.BASE,
    SupplyCategory.FILLING,
    SupplyCategory.TOPPING,
    SupplyCategory.FLAVORING,
    SupplyCategory.COLORING,
    SupplyCategory.ADDITIVE,
    SupplyCategory.GARNISH,
}

# ------------------------------
# Tipo de Tag de Produto
# ------------------------------
class SupplyProductTagType(models.TextChoices):
    CATALOG_CATEGORY = "catalog_category", "Categoria de Catálogo"
    DEPARTMENT = "department", "Departamento"
    SUBCATEGORY = "subcategory", "Subcategoria"
    SIZE = "size", "Tamanho"
    TYPE = "type", "Tipo"
    FORMAT = "format", "Formato"
    FORM_TYPE = "form_type", "Tipo de Forma"
    SEASONALITY = "seasonality", "Sazonalidade"
    COLOR = "color", "Cor"
    BRAND = "brand", "Marca"
    PATTERN = "pattern", "Estampa"

# ------------------------------
# Tag Comercial/Filtro
# ------------------------------
class SupplyProductTag(models.Model):
    name = models.CharField("Nome", max_length=64)
    tag_type = models.CharField("Tipo de Tag", max_length=32, choices=SupplyProductTagType.choices)

    class Meta:
        verbose_name = "Tag de Produto"
        verbose_name_plural = "Tags de Produtos"
        unique_together = ("name", "tag_type")
        ordering = ["tag_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_tag_type_display()})"

# ------------------------------
# Item de Suprimento
# ------------------------------
class SupplyItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField("SKU", max_length=32, unique=True)
    name = models.CharField("Nome", max_length=128)
    description = models.TextField("Descrição", blank=True)
    barcode = models.CharField("Código de barras", max_length=64, blank=True)

    unit_of_measure = models.CharField(
        "Unidade de medida",
        max_length=16,
        choices=UnitOfMeasureEnum.choices
    )

    category = models.CharField("Categoria", max_length=32, choices=SupplyCategory.choices)
    origin_country = models.CharField("País de origem", max_length=64, blank=True)
    regulatory_code = models.CharField("Código regulatório", max_length=64, blank=True)
    expiration_control = models.BooleanField("Controla validade", default=False)
    batch_control = models.BooleanField("Controla lote", default=False)

    is_ingredient = models.BooleanField(
        "Pode ser usado como ingrediente?", default=False,
        help_text="Use apenas para itens comestíveis e aplicáveis em receitas."
    )

    is_active = models.BooleanField("Ativo", default=True)
    tags = models.ManyToManyField(SupplyProductTag, related_name="supply_items", blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    # ----------- Funções auxiliares -----------

    @property
    def category_purpose(self):
        return SupplyCategory.help_text(self.category)

    @property
    def is_valid_ingredient(self):
        return self.is_ingredient and self.category in INGREDIENT_CATEGORIES

    @property
    def display_name(self):
        return f"{self.name} ({self.unit_of_measure})"

    @property
    def unit_description(self):
        return get_unit_description(self.unit_of_measure)

    @property
    def image_url(self):
        cover = self.images.filter(is_cover=True).first()
        return cover.image.url if cover and cover.image else "/static/img/no-image.png"

    def get_tag_names(self, tag_type=None):
        """Retorna nomes de tags, opcionalmente filtrando por tipo."""
        tags = self.tags.all()
        if tag_type:
            tags = tags.filter(tag_type=tag_type)
        return [tag.name for tag in tags]

    def main_image(self):
        """Retorna a imagem de capa, se houver."""
        return self.images.filter(is_cover=True).first()

    def has_expiration(self):
        return self.batches.filter(expiration_date__isnull=False).exists()

    def next_expiration(self):
        """
        Retorna a data de vencimento mais próxima (passada ou futura), considerando todos os lotes.
        """
        lotes = self.batches.filter(expiration_date__isnull=False).order_by('expiration_date')
        return lotes.first().expiration_date if lotes.exists() else None
    def next_valid_expiration(self):
        """
        Opcional: retorna a próxima data futura de vencimento, ignorando lotes vencidos.
        Útil para outros relatórios, mas não usado no admin se quiser mostrar 'Vencido'.
        """
        today = datetime.date.today()
        lotes = self.batches.filter(expiration_date__gte=today).order_by('expiration_date')
        return lotes.first().expiration_date if lotes.exists() else None

    def preview_image_thumb(self):
        """Gera HTML para visualização da imagem no admin."""
        image = self.main_image()
        return image.render_image_thumb(width=60) if image else format_html("<i>sem imagem</i>")
    preview_image_thumb.short_description = "Preview"
    

    def clean(self):
        if self.is_ingredient and self.category not in INGREDIENT_CATEGORIES:
            from django.core.exceptions import ValidationError
            raise ValidationError("Categoria incompatível com ingrediente comestível.")

    def save(self, *args, **kwargs):
        self.sku = self.sku.strip().upper().replace(" ", "")
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Inativo" if not self.is_active else ""
        return f"{self.name} ({self.sku}) {'[Inativo]' if not self.is_active else ''}".strip()


    class Meta:
        verbose_name = "Item de Suprimento"
        verbose_name_plural = "Itens de Suprimentos"
        ordering = ["name"]


# ------------------------------
# Lote de um Suprimento
# ------------------------------
class SupplyBatch(models.Model):
    supply_item = models.ForeignKey(
        SupplyItem,
        on_delete=models.CASCADE,
        related_name="batches",
        verbose_name="Item de Suprimento"
    )
    batch_code = models.CharField("Código do lote", max_length=64)
    expiration_date = models.DateField("Data de validade")
    quantity = models.DecimalField("Quantidade", max_digits=10, decimal_places=2)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    def __str__(self):
        return f"Lote {self.batch_code} - {self.supply_item.name}"

    class Meta:
        verbose_name = "Lote de Suprimento"
        verbose_name_plural = "Lotes de Suprimentos"
        ordering = ["-expiration_date"]
        unique_together = ("supply_item", "batch_code")

class ImageType(models.TextChoices):
    PRINCIPAL = 'principal', _('Principal')
    EMBALAGEM = 'embalagem', _('Foto da Embalagem')
    ROTULO = 'rotulo', _('Rótulo / Informações Nutricionais')
    DETALHE = 'detalhe', _('Detalhe Visual')
    CONTEXTO = 'contexto', _('Uso no Contexto')

class SupplyImage(models.Model):
    supply_item = models.ForeignKey(
        SupplyItem,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Suprimento"
    )
    image = models.ImageField("Imagem", upload_to="supplies/images/", null=True, blank=True)
    image_type = models.CharField("Tipo", max_length=20, choices=ImageType.choices)
    is_cover = models.BooleanField("Imagem de capa", default=False)

    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Imagem de Suprimento"
        verbose_name_plural = "Imagens de Suprimento"
        ordering = ["-is_cover", "image_type"]

    def __str__(self):
        tipo = self.get_image_type_display()
        return f"{tipo} - {self.supply_item.name}" + (" [CAPA]" if self.is_cover else "")

    def has_image(self) -> bool:
        return bool(self.image and hasattr(self.image, "url"))

    def save(self, *args, **kwargs):
        if self.is_cover:
            SupplyImage.objects.filter(supply_item=self.supply_item, is_cover=True).exclude(pk=self.pk).update(is_cover=False)
        super().save(*args, **kwargs)

    def get_image_url(self) -> str:
        return self.image.url if self.has_image() else "/static/img/no-image.png"

    def render_image_thumb(self, width=80) -> str:
        if self.has_image():
            return format_html(
                '<img src="{}" width="{}" style="object-fit:cover; border-radius:4px; border:1px solid #ccc;" />',
                self.get_image_url(), width
            )
        return format_html('<span style="opacity: 0.5;">Sem imagem</span>')

    def render_image_large(self, width=400) -> str:
        if self.has_image():
            return format_html(
                '''
                <a href="{0}" target="_blank">
                    <img src="{0}" width="{1}" style="border-radius: 8px; border: 1px solid #ccc;" />
                </a>
                ''',
                self.get_image_url(), width
            )

class SupplyNutritionInfo(models.Model):
    supply_item = models.OneToOneField(
        "supplies.SupplyItem",  # ou apenas SupplyItem se importar diretamente
        on_delete=models.CASCADE,
        related_name="nutrition_info"
    )
    serving_size = models.CharField("Porção", max_length=64)
    calories = models.DecimalField("Calorias", max_digits=6, decimal_places=2, null=True, blank=True)
    protein = models.DecimalField("Proteínas (g)", max_digits=6, decimal_places=2, null=True, blank=True)
    fat = models.DecimalField("Gorduras Totais (g)", max_digits=6, decimal_places=2, null=True, blank=True)
    saturated_fat = models.DecimalField("Gorduras Saturadas (g)", max_digits=6, decimal_places=2, null=True, blank=True)
    trans_fat = models.DecimalField("Gorduras Trans (g)", max_digits=6, decimal_places=2, null=True, blank=True)
    carbohydrates = models.DecimalField("Carboidratos (g)", max_digits=6, decimal_places=2, null=True, blank=True)
    sugars = models.DecimalField("Açúcares (g)", max_digits=6, decimal_places=2, null=True, blank=True)
    fiber = models.DecimalField("Fibras (g)", max_digits=6, decimal_places=2, null=True, blank=True)
    sodium = models.DecimalField("Sódio (mg)", max_digits=6, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Informação Nutricional"
        verbose_name_plural = "Informações Nutricionais"
    
    

    # -----------------------------------
    # Funções auxiliares
    # -----------------------------------

    def __str__(self):
        kcal = f"{self.calories:.0f} kcal" if self.calories is not None else "sem calorias"
        return f"Nutrição - {self.supply_item.name} ({kcal} / {self.serving_size})"


    def summary(self) -> str:
        """Resumo simplificado da porção e calorias"""
        return f"{self.calories or 0:.0f} kcal por {self.serving_size}"

    def macro_distribution(self) -> dict:
        """
        Percentuais relativos de macronutrientes:
        - Proteína
        - Gordura
        - Carboidrato
        """
        total = sum(filter(None, [
            self.protein or 0,
            self.fat or 0,
            self.carbohydrates or 0,
        ]))
        if total == 0:
            return {}
        return {
            "protein_pct": round((self.protein or 0) / total * 100, 1),
            "fat_pct": round((self.fat or 0) / total * 100, 1),
            "carb_pct": round((self.carbohydrates or 0) / total * 100, 1),
        }

    def is_high_calorie(self) -> bool:
        """Verifica se o item é considerado hipercalórico"""
        return (self.calories or 0) >= 400

    def is_low_sodium(self) -> bool:
        """Verifica se o item tem baixo teor de sódio"""
        return (self.sodium or 0) < 120

    def render_nutrition_table(self) -> str:
        """Renderiza uma tabela HTML com as informações nutricionais"""
        rows = []
        campos = [
            ("Calorias", self.calories, "kcal"),
            ("Proteínas", self.protein, "g"),
            ("Gorduras Totais", self.fat, "g"),
            ("Gorduras Saturadas", self.saturated_fat, "g"),
            ("Gorduras Trans", self.trans_fat, "g"),
            ("Carboidratos", self.carbohydrates, "g"),
            ("Açúcares", self.sugars, "g"),
            ("Fibras", self.fiber, "g"),
            ("Sódio", self.sodium, "mg"),
        ]
        for label, val, unit in campos:
            if val is not None:
                rows.append(f"<tr><td>{label}</td><td style='text-align:right'>{val:.2f} {unit}</td></tr>")
        return format_html('<table style="font-size:13px; border-collapse:collapse;">{}</table>', "".join(rows))

    def __str__(self):
        return f"Nutrição: {self.summary()}"

from django.db import models
from django.utils.html import format_html


class SupplyIngredientDetail(models.Model):
    supply_item = models.OneToOneField(
        "SupplyItem",  # aspas para evitar import circular
        on_delete=models.CASCADE,
        related_name="ingredient_detail",
        verbose_name="Item de Suprimento"
    )
    ingredient_list = models.TextField("Ingredientes", blank=True)
    contains_gluten = models.BooleanField("Contém glúten?", default=False)
    is_vegan = models.BooleanField("É vegano?", default=False)
    warnings = models.TextField("Advertências de consumo", blank=True)

    class Meta:
        verbose_name = "Composição e Advertências"
        verbose_name_plural = "Composições e Advertências"

    def __str__(self):
        return f"Composição - {self.supply_item.name}"

    # ------------------------
    # Funções auxiliares
    # ------------------------

    def has_ingredient_info(self) -> bool:
        """Retorna True se houver lista de ingredientes preenchida."""
        return bool(self.ingredient_list.strip())

    def gluten_status_display(self) -> str:
        """Texto legível sobre presença de glúten."""
        return "Contém glúten" if self.contains_gluten else "Não contém glúten"

    def vegan_status_display(self) -> str:
        """Texto legível sobre característica vegana."""
        return "Vegano" if self.is_vegan else "Não vegano"

    def short_ingredients(self, max_words=10) -> str:
        """Retorna os primeiros ingredientes para visualização resumida."""
        if not self.ingredient_list:
            return "-"
        words = self.ingredient_list.strip().split()
        return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

    def render_summary_html(self) -> str:
        """Renderiza um bloco HTML com resumo da composição para o admin."""
        if not self.has_ingredient_info():
            return format_html('<span style="color:gray;">Sem composição</span>')

        gluten = "✅" if self.contains_gluten else "❌"
        vegan = "🌱" if self.is_vegan else "🚫"
        return format_html(
            "<strong>Glúten:</strong> {}<br><strong>Vegano:</strong> {}<br><strong>Ingredientes:</strong> {}",
            gluten,
            vegan,
            self.short_ingredients(15)
        )

    render_summary_html.short_description = "Resumo"
    render_summary_html.allow_tags = True

    def clean(self):
        """Validações adicionais (se desejar bloquear inconsistências)."""
        if self.is_vegan and self.contains_gluten:
            from django.core.exceptions import ValidationError
            raise ValidationError("Item não pode ser vegano e conter glúten ao mesmo tempo.")



