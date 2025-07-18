from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from supplies.models import SupplyItem, SupplyBatch, SupplyNutritionInfo
from supplies.serializers import (
    SupplyItemSerializer,
    SupplyBatchSerializer,
    SupplyItemWithBatchSerializer,
    BulkSupplyItemWithBatchSerializer,
    SupplyNutritionInfoSerializer 
)

class BasePaginatedView(APIView):
    def paginate_queryset(self, queryset, request, serializer_class):
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 10)
        paginator = Paginator(queryset, page_size)
        try:
            paginated_items = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            paginated_items = paginator.page(1)

        serializer = serializer_class(paginated_items, many=True, context={"request": request})
        return {
            "count": paginator.count,
            "next": paginated_items.next_page_number() if paginated_items.has_next() else None,
            "previous": paginated_items.previous_page_number() if paginated_items.has_previous() else None,
            "results": serializer.data,
        }


class SupplyItemListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Listar suprimentos com filtros",
        operation_description="Permite buscar por nome, SKU ou categoria.",
        manual_parameters=[
            openapi.Parameter("name", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("sku", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("category", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        tags=["supplies"]
    )
    def get(self, request):
        queryset = SupplyItem.objects.filter(is_active=True)
        name = request.query_params.get("name")
        sku = request.query_params.get("sku")
        category = request.query_params.get("category")

        if name:
            queryset = queryset.filter(name__icontains=name)
        if sku:
            queryset = queryset.filter(sku__icontains=sku)
        if category:
            queryset = queryset.filter(category=category)

        # Paginação simples
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 10)
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        serializer = SupplyItemSerializer(page_obj, many=True, context={"request": request})

        return Response({
            "count": paginator.count,
            "results": serializer.data,
            "next": page_obj.next_page_number() if page_obj.has_next() else None,
            "previous": page_obj.previous_page_number() if page_obj.has_previous() else None,
        })


class SupplyItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create supply item",
        operation_description="Creates and registers a new supply item.",
        request_body=SupplyItemSerializer,
        responses={201: SupplyItemSerializer, 400: "Bad Request"},
        tags=["supplies"]
    )
    def post(self, request):
        serializer = SupplyItemSerializer(data=request.data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(SupplyItemSerializer(item).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SupplyItemRetrieveView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Retrieve supply item",
        operation_description="Returns details of a specific supply item by its ID.",
        responses={200: SupplyItemSerializer, 404: "Not Found"},
        tags=["supplies"]
    )
    def get(self, request, pk):
        try:
            item = SupplyItem.objects.get(pk=pk, is_active=True)
            return Response(SupplyItemSerializer(item).data)
        except SupplyItem.DoesNotExist:
            return Response({"error": "Supply item not found"}, status=404)


class SupplyItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Fully update supply item",
        operation_description="Updates all fields of a supply item.",
        request_body=SupplyItemSerializer,
        responses={200: SupplyItemSerializer, 404: "Not Found"},
        tags=["supplies"]
    )
    def put(self, request, pk):
        try:
            item = SupplyItem.objects.get(pk=pk)
        except SupplyItem.DoesNotExist:
            return Response({"error": "Supply item not found"}, status=404)

        serializer = SupplyItemSerializer(item, data=request.data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(SupplyItemSerializer(item).data)
        return Response(serializer.errors, status=400)


class SupplyItemPartialUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Partially update supply item",
        operation_description="Updates selected fields of a supply item.",
        request_body=SupplyItemSerializer,
        responses={200: SupplyItemSerializer, 404: "Not Found"},
        tags=["supplies"]
    )
    def patch(self, request, pk):
        try:
            item = SupplyItem.objects.get(pk=pk)
        except SupplyItem.DoesNotExist:
            return Response({"error": "Supply item not found"}, status=404)

        serializer = SupplyItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            return Response(SupplyItemSerializer(item).data)
        return Response(serializer.errors, status=400)


class SupplyItemDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Soft delete supply item",
        operation_description="Marks the supply item as inactive instead of deleting.",
        responses={204: "No Content", 404: "Not Found"},
        tags=["supplies"]
    )
    def delete(self, request, pk):
        try:
            item = SupplyItem.objects.get(pk=pk)
        except SupplyItem.DoesNotExist:
            return Response({"error": "Supply item not found"}, status=404)

        item.is_active = False
        item.save()
        return Response(status=204)


class SupplyBatchListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplyBatchSerializer

    def get_queryset(self):
        queryset = SupplyBatch.objects.select_related("supply_item").all()
        supply_item_id = self.request.query_params.get("supply_item_id")
        if supply_item_id:
            queryset = queryset.filter(supply_item_id=supply_item_id)
        return queryset

    @swagger_auto_schema(
        operation_summary="Listar lotes de suprimento",
        manual_parameters=[
            openapi.Parameter(
                "supply_item_id", openapi.IN_QUERY, description="Filtrar por ID do item",
                type=openapi.TYPE_STRING
            )
        ],
        tags=["supply-batches"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Criar novo lote de suprimento",
        tags=["supply-batches"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class SupplyItemWithBatchCreateView(APIView):
    #permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Criar múltiplos itens com lote (opcional)",
        operation_description="Cria itens de suprimentos com ou sem lote associado. Caso o item controle lote, o campo `supply_batch` é obrigatório.",
        request_body=SupplyItemWithBatchSerializer(many=True),
        responses={
            201: openapi.Response(description="Itens criados com sucesso"),
            400: "Erro de validação nos dados enviados"
        },
        tags=["supplies"]
    )
    def post(self, request):
        serializer = SupplyItemWithBatchSerializer(
            data=request.data,
            many=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Itens criados com sucesso!"}, status=status.HTTP_201_CREATED)

class SupplyNutritionInfoRetrieveView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Obter informações nutricionais do item",
        operation_description="Retorna os dados nutricionais de um item de suprimento.",
        responses={200: SupplyNutritionInfoSerializer, 404: "Not Found"},
        tags=["supply-nutrition"]
    )
    def get(self, request, supply_item_id):
        try:
            supply_item = SupplyItem.objects.get(pk=supply_item_id, is_active=True)
            nutrition = supply_item.nutrition_info
            if not nutrition:
                return Response({"detail": "Informações nutricionais não cadastradas."}, status=404)
            return Response(SupplyNutritionInfoSerializer(nutrition).data)
        except SupplyItem.DoesNotExist:
            return Response({"detail": "Item de suprimento não encontrado."}, status=404)


class SupplyNutritionInfoUpsertView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Cadastrar ou atualizar informações nutricionais",
        operation_description="Se já existir, atualiza. Caso contrário, cria nova entrada nutricional.",
        request_body=SupplyNutritionInfoSerializer,
        responses={200: SupplyNutritionInfoSerializer, 400: "Bad Request", 404: "Not Found"},
        tags=["supply-nutrition"]
    )
    def put(self, request, supply_item_id):
        try:
            supply_item = SupplyItem.objects.get(pk=supply_item_id)
        except SupplyItem.DoesNotExist:
            return Response({"detail": "Item de suprimento não encontrado."}, status=404)

        try:
            nutrition = supply_item.nutrition_info
            serializer = SupplyNutritionInfoSerializer(nutrition, data=request.data)
        except SupplyNutritionInfo.DoesNotExist:
            serializer = SupplyNutritionInfoSerializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save(supply_item=supply_item)
            return Response(SupplyNutritionInfoSerializer(instance).data, status=200)

        return Response(serializer.errors, status=400)


class SupplyNutritionInfoDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Remover informações nutricionais do item",
        operation_description="Deleta as informações nutricionais associadas a um item de suprimento.",
        responses={204: "No Content", 404: "Not Found"},
        tags=["supply-nutrition"]
    )
    def delete(self, request, supply_item_id):
        try:
            supply_item = SupplyItem.objects.get(pk=supply_item_id)
            nutrition = supply_item.nutrition_info
            nutrition.delete()
            return Response(status=204)
        except SupplyItem.DoesNotExist:
            return Response({"detail": "Item de suprimento não encontrado."}, status=404)
        except SupplyNutritionInfo.DoesNotExist:
            return Response({"detail": "Informações nutricionais não encontradas."}, status=404)