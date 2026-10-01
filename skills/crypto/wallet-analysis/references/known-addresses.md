# Known addresses (labels)

Knowledge base for labeling counterparties. Extend it as analyses accumulate.
The `analyze_wallet.py` script embeds a copy of these maps (`KNOWN_CONTRACTS`,
`KNOWN_CEX`). When you identify a new address via Etherscan, add it here
**and** to the script.

## How to confirm a label without an API key

Etherscan shows the "public name tag" on the address page. No key needed:

```
WebFetch  https://etherscan.io/address/<ADDR>
prompt: "What is the public name tag / label of this address? Exchange (Binance/Kraken/Coinbase)? Contract or EOA?"
```

This works for: exchanges (Binance 10, Kraken 4, Coinbase 2...), protocols, verified
contracts, deposit addresses, tagged entities. This is THE method to go from an
anonymous address to an identity.

## Heuristic signal: exchange / automated service

A **nonce > 100,000** (number of outgoing tx) = high-frequency automated address:
CEX hot wallet, MEV bot, market-maker, relayer. **This is never the owner's personal
wallet**; it is a source/destination of funds. Always confirm the exact label via
Etherscan before naming the exchange.

## CEX hot wallets (verified sample)

| Address | Label |
|---|---|
| 0x85b931a32a0725be14285b66f1a22178c672d69b | Binance 10 |
| 0x564286362092d8e7936f0549571a803b203aaced | Binance 3 |
| 0x28c6c06298d514db089934071355e5743bf21d60 | Binance 14 |
| 0x21a31ee1afc51d94c2efccaa2092ad1028285549 | Binance 15 |
| 0xdfd5293d8e347dfe59e90efd55b2956a1343963d | Binance 16 |
| 0x9696f59e4d72e237be84ffd425dcad154bf96976 | Binance 18 |
| 0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0 | Kraken 4 |
| 0xfa52274dd61e1643d2205169732f29114bc240b3 | Kraken 1 |
| 0x71660c4005ba85c37ccec55d0c4493e66fe775d3 | Coinbase 1 |
| 0x503828976d22510aad0201ac7ec88293211d23da | Coinbase 2 |
| 0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740 | Coinbase 3 |
| 0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43 | Coinbase 10 |
| 0xe93381fb4c4f14bda253907b18fad305d799241a | Huobi |

> Note: "SimpleSwap", "ChangeNOW", "FixedFloat" = non-custodial instant swaps
> often used as off-ramp relays / to break the on-chain link.

## Common contracts (to exclude from "people")

| Address | Label |
|---|---|
| 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2 | WETH (Wrapped Ether) |
| 0x00000000006c3852cbef3e08e8df289169ede581 | OpenSea Seaport 1.1 |
| 0x00000000000000adc04c56bf30ac9d3c0aaf14dc | OpenSea Seaport 1.5 |
| 0x7f268357a8c2552623316e2562d90e642bb538e5 | OpenSea Wyvern v2 |
| 0xdef171fe48cf0115b1d80b88dc8eab59176fee57 | ParaSwap Augustus (DEX) |
| 0x1111111254eeb25477b68fb85ed929f73a960582 | 1inch v5 Router |
| 0x7a250d5630b4cf539739df2c5dacb4c659f2488d | Uniswap V2 Router |
| 0xe592427a0aece92de3edee1f18e0157c05861564 | Uniswap V3 Router |
| 0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45 | Uniswap Universal Router |

## Special addresses

| Address | Meaning |
|---|---|
| 0x0000000000000000000000000000000000000000 | burn / mint (zero address) - ignore as a counterparty |
| 0x000000000000000000000000000000000000dead | burn address |
