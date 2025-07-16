from django import forms
from .models import Cake

class CakeForm(forms.ModelForm):
    class Meta:
        model = Cake
        fields = [
            "name",
            "slug",  # precisa estar aqui
            "description",
            "category",
            "customizable",
            "estimated_weight_kg",
            "is_available_for_delivery",
            "is_available_for_pickup",
            "is_active",
            "production_time_days",
            "internal_notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "slug" in self.fields:
            self.fields["slug"].required = False
            self.fields["slug"].disabled = True
