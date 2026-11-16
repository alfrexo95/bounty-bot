import pytest
from bounty_bot import compute_market_cap

@pytest.fixture
def usdc_pair():
    return {
        "symbol": "ABC/USDC",
        "price": "2.5",  # USDC price, already USD
        "quoteCurrency": "USDC",
        "circulatingSupply": "1000000",
    }

@pytest.fixture
def eth_pair():
    return {
        "symbol": "XYZ/ETH",
        "price": "0.01",  # price in ETH
        "quoteCurrency": "ETH",
        "circulatingSupply": "500000",
    }

def test_market_cap_usdc_pair(usdc_pair):
    market_cap = compute_market_cap(usdc_pair)
    # Expected: 2.5 USD * 1,000,000 = 2,500,000 USD
    assert market_cap == 2_500_000.0

def test_market_cap_eth_pair(eth_pair):
    # ETH conversion rate is mocked as 1800 USD in bounty_bot.get_usd_conversion_rate
    # price in ETH = 0.01, so USD price = 0.01 * 1800 = 18 USD
    # market cap = 18 * 500,000 = 9,000,000 USD
    market_cap = compute_market_cap(eth_pair)
    assert market_cap == 9_000_000.0
