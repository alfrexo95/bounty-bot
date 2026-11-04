```javascript
export function get_market_cap(pair) {
    let price, volume;
    if (pair.quote === "USDC") {
        price = quote.quote;
    } else {
        price = pair.quote;
    }
    volume = pair.volume_24h;
    return (price * volume * 0.1).toFixed(2);
}
```