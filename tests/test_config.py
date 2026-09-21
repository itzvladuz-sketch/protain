from services.config import BotConfig


def test_config_never_allows_less_than_50_stars(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("FRAGMENT_WALLET_MNEMONIC", "word " * 24)
    monkeypatch.setenv("TON_WALLET_ADDRESS", "UQtest")
    monkeypatch.setenv("MIN_STARS_AMOUNT", "1")

    assert BotConfig.load().min_stars_amount == 50


def test_config_reads_optional_wallet_account(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("FRAGMENT_WALLET_MNEMONIC", "word " * 12)
    monkeypatch.setenv("TON_WALLET_ADDRESS", "UQtest")
    monkeypatch.setenv("FRAGMENT_WALLET_ADDRESS", "UQselected")
    monkeypatch.setenv("FRAGMENT_ACCOUNT_INDEX", "7")

    config = BotConfig.load()

    assert config.fragment_wallet_address == "UQselected"
    assert config.fragment_account_index == 7


def test_config_rejects_invalid_wallet_account(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("FRAGMENT_WALLET_MNEMONIC", "word " * 12)
    monkeypatch.setenv("TON_WALLET_ADDRESS", "UQtest")
    monkeypatch.setenv("FRAGMENT_ACCOUNT_INDEX", "-1")

    try:
        BotConfig.load()
    except ValueError as exc:
        assert "FRAGMENT_ACCOUNT_INDEX" in str(exc)
    else:
        raise AssertionError("invalid account index was accepted")
