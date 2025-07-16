from django.urls import path

from .views import (
    CakeListView,
    CakeCreateView,
    CakeRetrieveView,
    CakeUpdateView,
    CakePartialUpdateView,
    CakeDeleteView,
    CakeRetrieveBySlugView,
    CakeSizeListView,
    CakeCompositionDetailView,
    CakeImageListView,
    CakeNutritionalInfoView
)

urlpatterns = [
    # Cakes
    path("cakes/", CakeListView.as_view(), name="cake-list"),
    path("cakes/create/", CakeCreateView.as_view(), name="cake-create"),
    path("cakes/<uuid:pk>/", CakeRetrieveView.as_view(), name="cake-detail"),
    path("cakes/<uuid:pk>/update/", CakeUpdateView.as_view(), name="cake-update"),
    path("cakes/<uuid:pk>/partial-update/", CakePartialUpdateView.as_view(), name="cake-partial-update"),
    path("cakes/<uuid:pk>/delete/", CakeDeleteView.as_view(), name="cake-delete"),
    path("cakes/slug/<slug:slug>/", CakeRetrieveBySlugView.as_view(), name="cake-detail-slug"),
    path("cakes/<uuid:cake_id>/sizes/", CakeSizeListView.as_view(), name="cake-sizes"),
    path("cakes/<uuid:cake_id>/composition/", CakeCompositionDetailView.as_view(), name="cake-composition"),
    path("cakes/<uuid:cake_id>/images/", CakeImageListView.as_view(), name="cake-images"),
    path("cakes/<uuid:cake_id>/nutritional-info/", CakeNutritionalInfoView.as_view(), name="cake-nutritional-info"),
]
