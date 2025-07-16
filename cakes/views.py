from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from cakes.models import Cake
from cakes.serializers import (
    CakeSerializer,
    CakeSizeSerializer,
    CakeCompositionSerializer,
    CakeImageSerializer,
    NutritionalInfoSerializer
)
# View base com paginação customizada
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

# Listagem de bolos
class CakeListView(BasePaginatedView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="List all cakes",
        operation_description="Retrieve a paginated list of all active cakes.",
        manual_parameters=[
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        tags=["cakes"]
    )
    def get(self, request):
        queryset = Cake.objects.filter(is_active=True).order_by("name")
        return Response(self.paginate_queryset(queryset, request, CakeSerializer))

# Criação de bolo
class CakeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create a new cake",
        operation_description="Create and register a new cake in the system.",
        request_body=CakeSerializer,
        responses={201: CakeSerializer, 400: "Bad request"},
        tags=["cakes"]
    )
    def post(self, request):
        serializer = CakeSerializer(data=request.data)
        if serializer.is_valid():
            cake = serializer.save()
            return Response(CakeSerializer(cake).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Detalhe do bolo
class CakeRetrieveView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Retrieve cake by ID",
        operation_description="Get cake details by its ID.",
        responses={200: CakeSerializer, 404: "Cake not found"},
        tags=["cakes"]
    )
    def get(self, request, pk):
        try:
            cake = Cake.objects.get(pk=pk, is_active=True)
            return Response(CakeSerializer(cake).data)
        except Cake.DoesNotExist:
            return Response({"error": "Cake not found"}, status=status.HTTP_404_NOT_FOUND)

# Atualização completa
class CakeUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Fully update a cake",
        operation_description="Update all attributes of a cake by its ID.",
        request_body=CakeSerializer,
        responses={200: CakeSerializer, 404: "Cake not found"},
        tags=["cakes"]
    )
    def put(self, request, pk):
        try:
            cake = Cake.objects.get(pk=pk)
        except Cake.DoesNotExist:
            return Response({"error": "Cake not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CakeSerializer(cake, data=request.data)
        if serializer.is_valid():
            cake = serializer.save()
            return Response(CakeSerializer(cake).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Atualização parcial
class CakePartialUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Partially update a cake",
        operation_description="Partially update one or more attributes of a cake.",
        request_body=CakeSerializer,
        responses={200: CakeSerializer, 404: "Cake not found"},
        tags=["cakes"]
    )
    def patch(self, request, pk):
        try:
            cake = Cake.objects.get(pk=pk)
        except Cake.DoesNotExist:
            return Response({"error": "Cake not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CakeSerializer(cake, data=request.data, partial=True)
        if serializer.is_valid():
            cake = serializer.save()
            return Response(CakeSerializer(cake).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Remoção lógica (soft delete)
class CakeDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Soft delete a cake",
        operation_description="Marks the cake as inactive without removing from the database.",
        responses={204: "No content", 404: "Cake not found"},
        tags=["cakes"]
    )
    def delete(self, request, pk):
        try:
            cake = Cake.objects.get(pk=pk)
        except Cake.DoesNotExist:
            return Response({"error": "Cake not found"}, status=status.HTTP_404_NOT_FOUND)

        cake.is_active = False
        cake.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CakeRetrieveBySlugView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Retrieve cake by slug",
        operation_description="Get public cake details using a slug (SEO friendly).",
        responses={200: CakeSerializer, 404: "Cake not found"},
        tags=["cakes"]
    )
    def get(self, request, slug):
        try:
            cake = Cake.objects.get(slug=slug, is_active=True)
            return Response(CakeSerializer(cake).data)
        except Cake.DoesNotExist:
            return Response({"error": "Cake not found"}, status=status.HTTP_404_NOT_FOUND)

class CakeSizeListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="List cake sizes",
        operation_description="Get list of available sizes and prices for a specific cake.",
        responses={200: CakeSizeSerializer(many=True), 404: "Cake not found"},
        tags=["cakes"]
    )
    def get(self, request, cake_id):
        sizes = CakeSize.objects.filter(cake_id=cake_id)
        if not sizes.exists():
            return Response({"error": "Cake not found or no sizes available"}, status=404)
        return Response(CakeSizeSerializer(sizes, many=True).data)

class CakeCompositionDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Get cake composition",
        operation_description="Retrieve flavor, topping, ingredients and allergens of a cake.",
        responses={200: CakeCompositionSerializer, 404: "Composition not found"},
        tags=["cakes"]
    )
    def get(self, request, cake_id):
        try:
            composition = CakeComposition.objects.prefetch_related(
                "flavors", "ingredients", "allergens"
            ).get(cake_id=cake_id)
            return Response(CakeCompositionSerializer(composition).data)
        except CakeComposition.DoesNotExist:
            return Response({"error": "Composition not found"}, status=404)

class CakeImageListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="List cake images",
        operation_description="Get all images of the cake by type (principal, galeria, etc).",
        responses={200: CakeImageSerializer(many=True), 404: "No images found"},
        tags=["cakes"]
    )
    def get(self, request, cake_id):
        images = CakeImage.objects.filter(cake_id=cake_id)
        if not images.exists():
            return Response({"error": "No images found"}, status=404)
        return Response(CakeImageSerializer(images, many=True).data)

class CakeNutritionalInfoView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Get nutritional info",
        operation_description="Retrieve nutritional values per portion for a specific cake.",
        responses={200: NutritionalInfoSerializer, 404: "Nutritional info not found"},
        tags=["cakes"]
    )
    def get(self, request, cake_id):
        try:
            cake = Cake.objects.get(pk=cake_id, is_active=True)
            info = cake.nutritional_info
            return Response(NutritionalInfoSerializer(info).data)
        except Cake.DoesNotExist:
            return Response({"error": "Cake not found"}, status=404)
        except NutritionalInfo.DoesNotExist:
            return Response({"error": "Nutritional info not found"}, status=404)


