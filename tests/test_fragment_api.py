import base64

import pytest

from services.fragment_api import FragmentAPIError, FragmentAPIService


def test_base64_12_word_seed_is_not_double_encoded() -> None:
    phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    encoded = base64.b64encode(phrase.encode()).decode()

    assert FragmentAPIService._as_base64_seed(encoded) == encoded


def test_plain_12_word_seed_is_encoded() -> None:
    phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

    assert base64.b64decode(FragmentAPIService._as_base64_seed(phrase)).decode() == phrase


@pytest.mark.asyncio
async def test_buy_stars_rejects_less_than_fragment_minimum_before_sdk_call() -> None:
    service = FragmentAPIService.__new__(FragmentAPIService)
    service.client = object()

    with pytest.raises(FragmentAPIError, match="минимум 50"):
        await service.buy_stars("@telegram_user", 49)
