from http import HTTPStatus
from urllib.parse import urlencode

import pytest
from django.conf import settings
from django.urls import reverse

from common.tests import common_detail_view_tests
from interactions.tests import ProductCommentTestFactory
from products.tests import ProductTestFactory, ProductTypeTestFactory


@pytest.fixture()
def product_type():
    return ProductTypeTestFactory()


@pytest.fixture()
def product_types():
    return ProductTypeTestFactory.create_batch(settings.PRODUCT_TYPES_PAGINATE_BY * 2)


@pytest.fixture()
def product():
    return ProductTestFactory()


@pytest.mark.django_db
def test_product_type_list_view(client, product_types):
    path = reverse('products:product-types')

    response = client.get(path)

    context_object_list = response.context_data.get('object_list')

    assert response.status_code == HTTPStatus.OK
    assert len(context_object_list) == len(product_types[:settings.PRODUCT_TYPES_PAGINATE_BY])


@pytest.mark.django_db
def test_product_list_view(client, product_type):
    products = ProductTestFactory.create_batch(settings.PRODUCTS_PAGINATE_BY * 2, product_type=product_type)

    path = reverse('products:products', args=(product_type.slug,))

    response = client.get(path)

    product_type.refresh_from_db()
    context_object_list = response.context_data.get('object_list')

    assert response.status_code == HTTPStatus.OK
    assert product_type.views == 1
    assert len(context_object_list) == len(products[:settings.PRODUCTS_PAGINATE_BY])


@pytest.mark.django_db
def test_product_detail_view(client, product):
    comments = ProductCommentTestFactory.create_batch(settings.COMMENTS_PAGINATE_BY * 2, product=product)

    path = product.get_absolute_url()

    response = client.get(path)

    assert response.status_code == HTTPStatus.OK
    common_detail_view_tests(response, product, comments)


@pytest.mark.parametrize(
    'search_type, expected_status',
    [
        ('product', HTTPStatus.FOUND),
        ('product_type', HTTPStatus.FOUND),
        ('nonexistent', HTTPStatus.BAD_REQUEST),
    ],
)
def test_search_redirect_view(client, search_type, expected_status):
    params = {
        'search_query': 'coffee',
        'search_type': search_type,
    }
    query_string = urlencode(params)
    path = reverse('products:search-redirect') + '?' + query_string

    response = client.get(path)

    assert response.status_code == expected_status


@pytest.mark.django_db
@pytest.mark.parametrize(
    'search_query, search_type, expected_results',
    [
        ('coffee', 'product_type', True),
        ('cOfFeE', 'product_type', True),
        ('cof', 'product_type', True),
        ('Coffee and coffee-related products.', 'product_type', True),
        ('Coffee AnD cOFFee-reLATeD', 'product_type', True),
        ('nonexistent_product_type', 'product_type', False),

        ('coffee', 'product', True),
        ('cOfFeE', 'product', True),
        ('cof', 'product', True),
        ('The best roasting!', 'product', True),
        ('ThE BE', 'product', True),
        ('nonexistent_product', 'product', False),
    ],
)
def test_search_list_view(client, search_query, search_type, expected_results):
    ProductTypeTestFactory.create(name='Coffee', description='Coffee and coffee-related products.')
    ProductTestFactory.create(name='Coffee', card_description='The best roasting!')

    params = {
        'search_query': search_query,
        'search_type': search_type,
    }
    query_string = urlencode(params)

    url_mapping = {
        'product_type': 'products:product-type-search',
        'product': 'products:product-search',
    }

    path = reverse(url_mapping[search_type]) + '?' + query_string

    response = client.get(path)

    assert response.status_code == HTTPStatus.OK
    assert bool(response.context_data['object_list']) is expected_results


if __name__ == '__main__':
    pytest.main()
