from django.db import models

class UnitOfMeasureEnum(models.TextChoices):
    UNIT = "un", "Unidade"
    GRAM = "g", "Grama"
    KILOGRAM = "kg", "Quilograma"
    MILLILITER = "ml", "Mililitro"
    LITER = "l", "Litro"
    SLICE = "fatia", "Fatia"


UNIT_DESCRIPTION_MAP = {
    UnitOfMeasureEnum.UNIT: "Unidade padrão",
    UnitOfMeasureEnum.GRAM: "Medida de massa",
    UnitOfMeasureEnum.KILOGRAM: "1000 gramas",
    UnitOfMeasureEnum.MILLILITER: "Medida de volume",
    UnitOfMeasureEnum.LITER: "1000 mililitros",
    UnitOfMeasureEnum.SLICE: "Porção individual",
}

def get_unit_description(code: str) -> str:
    """
    Retorna a descrição auxiliar da unidade, útil para tooltips ou explicações no admin.
    """
    return UNIT_DESCRIPTION_MAP.get(code, "")

def get_unit_choices_with_help():
    """
    Retorna uma lista de tuplas (value, label, help_text) para uso em interfaces ricas ou documentação.
    """
    return [
        (choice.value, choice.label, get_unit_description(choice))
        for choice in UnitOfMeasureEnum
    ]
