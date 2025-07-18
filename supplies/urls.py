from django.urls import path
from supplies.views import (
    SupplyItemListView,
    SupplyItemCreateView,
    SupplyItemRetrieveView,
    SupplyItemUpdateView,
    SupplyItemPartialUpdateView,
    SupplyItemDeleteView,
    SupplyBatchListCreateView,
    SupplyItemWithBatchCreateView,
    SupplyNutritionInfoRetrieveView,
    SupplyNutritionInfoUpsertView,
    SupplyNutritionInfoDeleteView 
)

urlpatterns = [
    path("", SupplyItemListView.as_view(), name="supply-list"),
    path("create/", SupplyItemCreateView.as_view(), name="supply-create"),
    path("<uuid:pk>/", SupplyItemRetrieveView.as_view(), name="supply-detail"),
    path("<uuid:pk>/update/", SupplyItemUpdateView.as_view(), name="supply-update"),
    path("<uuid:pk>/partial-update/", SupplyItemPartialUpdateView.as_view(), name="supply-partial-update"),
    path("<uuid:pk>/delete/", SupplyItemDeleteView.as_view(), name="supply-delete"),
    path("batches/", SupplyBatchListCreateView.as_view(), name="supply-batch-list-create"),
    path("items/with-batch/", SupplyItemWithBatchCreateView.as_view(), name="supply-item-with-batch"),
    path("<uuid:supply_item_id>/nutrition/",SupplyNutritionInfoRetrieveView.as_view(),name="supply-nutrition-retrieve"),
    path("<uuid:supply_item_id>/nutrition/update/",SupplyNutritionInfoUpsertView.as_view(),name="supply-nutrition-upsert"),
    path("<uuid:supply_item_id>/nutrition/delete/",SupplyNutritionInfoDeleteView.as_view(),name="supply-nutrition-delete"),
]
