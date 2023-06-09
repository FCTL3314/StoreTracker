from django.conf import settings
from rest_framework.viewsets import ModelViewSet

from api.permissions import IsAdminOrReadOnly
from api.v1.stores.paginators import StorePageNumberPagination
from api.v1.stores.serializers import StoreModelSerializer
from stores.models import Store


class StoreModelViewSet(ModelViewSet):
    queryset = Store.objects.order_by(*settings.STORES_ORDERING)
    permission_classes = (IsAdminOrReadOnly,)
    serializer_class = StoreModelSerializer
    pagination_class = StorePageNumberPagination
    lookup_field = "slug"
