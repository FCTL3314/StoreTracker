from datetime import timedelta
from http import HTTPStatus

import pytest
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils.timezone import now
from faker import Faker
from mixer.backend.django import mixer

from users.forms import LoginForm, RegistrationForm
from users.models import User
from utils.tests import generate_test_image

faker = Faker()

REMEMBER_ME_SESSION_AGE = ((60 * 60) * 24) * 14


@pytest.mark.django_db
def test_registration_create_view_get(client):
    response = client.get(reverse("users:registration"))

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.context_data["form"], RegistrationForm)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "expected_status, username, email, password",
    (
        [HTTPStatus.FOUND, faker.user_name(), faker.email(), faker.password()],
        [HTTPStatus.OK, "abc", faker.email(), faker.password()],
        [HTTPStatus.OK, faker.user_name(), "not_email", faker.password()],
        [HTTPStatus.OK, faker.user_name(), faker.email(), "123456"],
    ),
)
def test_registration_create_view_post(
    client, expected_status, username, email, password
):
    data = {
        "username": username,
        "email": email,
        "password1": password,
        "password2": password,
    }

    response = client.post(reverse("users:registration"), data=data)

    assert response.status_code == expected_status
    if response.status_code == HTTPStatus.FOUND:
        assert User.objects.filter(username=username, email=email).exists()


@pytest.mark.django_db
def test_login_view_get(client):
    response = client.get(reverse("users:login"))

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.context_data["form"], LoginForm)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "remember_me, session_age",
    (
        [True, REMEMBER_ME_SESSION_AGE],
        [False, ""],
    ),
)
def test_login_view_post(client, remember_me, session_age):
    password = faker.password()
    user = User.objects.create_user(
        username=faker.user_name(), email=faker.email(), password=password
    )

    data = {
        "username": user.username,
        "password": password,
        "remember_me": remember_me,
    }

    response = client.post(reverse("users:login"), data=data)

    assert response.status_code == HTTPStatus.FOUND
    assert response.cookies["sessionid"]["max-age"] == session_age


@pytest.mark.django_db
def test_profile_view(client, user):
    response = client.get(reverse("users:profile", args=(user.slug,)))

    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_pattern",
    (
        "users:profile-account",
        "users:profile-password",
        "users:profile-email",
    ),
)
def test_profile_settings_access(client, user, url_pattern):
    path = reverse(url_pattern)

    client.force_login(user)
    assert client.get(path).status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_profile_settings_account_view_post(client, user):
    client.force_login(user)

    path = reverse("users:profile-account")

    username = faker.user_name()
    first_name = faker.first_name()
    last_name = faker.last_name()
    image = generate_test_image()

    data = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "image": image,
    }

    response = client.post(path, data=data)

    user.refresh_from_db()

    assert response.status_code == HTTPStatus.FOUND
    assert user.username == username
    assert user.first_name == first_name
    assert user.last_name == last_name
    assert user.image


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_old_password_incorrect, new_password, error_expected",
    (
        [False, faker.password(), False],
        [False, "123", True],
        [True, faker.password(), True],
    ),
)
def test_profile_settings_password_view_post(
    client, is_old_password_incorrect, new_password, error_expected
):
    old_password = faker.password()
    user = mixer.blend("users.User", password=make_password(old_password))
    client.force_login(user)

    path = reverse("users:profile-password")

    data = {
        "old_password": faker.password() if is_old_password_incorrect else old_password,
        "new_password1": new_password,
        "new_password2": new_password,
    }

    response = client.post(path, data=data)

    user.refresh_from_db()

    if error_expected:
        assert response.status_code == HTTPStatus.OK
        assert not user.check_password(new_password)
    else:
        assert response.status_code == HTTPStatus.FOUND
        assert user.check_password(new_password)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_email, is_old_password_incorrect, error_expected",
    (
        [faker.email(), False, False],
        [faker.email(), True, True],
        ["not-email", False, True],
    ),
)
def test_profile_settings_email_view_post(
    client, new_email, is_old_password_incorrect, error_expected
):
    old_password = faker.password()
    user = mixer.blend(
        "users.User", password=make_password(old_password), is_verified=True
    )
    client.force_login(user)

    path = reverse("users:profile-email")

    data = {
        "email": new_email,
        "old_password": faker.password() if is_old_password_incorrect else old_password,
    }

    response = client.post(path, data=data)

    user.refresh_from_db()

    if error_expected:
        assert response.status_code == HTTPStatus.OK
        assert not user.email == new_email
    else:
        assert response.status_code == HTTPStatus.FOUND
        assert user.email == new_email
        assert user.is_verified is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_verified",
    (
        False,
        True,
    ),
)
def test_send_verification_email_view(client, is_verified):
    user = mixer.blend("users.User", is_verified=is_verified)
    client.force_login(user)

    path = reverse("users:send-verification-email", args=(user.email,))

    response = client.get(path)

    assert response.status_code == HTTPStatus.OK
    if is_verified:
        assert not user.emailverification_set.all()
    else:
        assert user.emailverification_set.all()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_verified, is_expired",
    (
        [False, False],
        [True, False],
        [False, True],
    ),
)
def test_email_verification_view(client, is_verified, is_expired):
    user = mixer.blend("users.User", is_verified=is_verified)
    if not is_expired:
        verification = mixer.blend("users.EmailVerification", user=user)
    else:
        verification = mixer.blend(
            "users.EmailVerification", user=user, expiration=now() - timedelta(days=2)
        )

    client.force_login(user)

    path = reverse(
        "users:email-verification",
        kwargs={"email": verification.user.email, "code": verification.code},
    )

    response = client.get(path)

    user.refresh_from_db()

    assert response.status_code == HTTPStatus.OK
    if is_expired:
        assert not user.is_verified
    elif not is_verified:
        assert user.is_verified


if __name__ == "__main__":
    pytest.main()
