---
name: wallet-analysis
description: On-chain relationship analysis of an EVM address (Ethereum & L2). Finds who funded a wallet, all EOA counterparties (vs contracts), filters out spam, and traces the origin chain of funds back to exchanges. No API key. Triggers on "analyze this wallet", "where does this address come from", "who funded this wallet", "find the linked wallets", "who is this wallet connected to".
compatibility: Requires curl + python3, network access. No API key. Works in Claude Code and any agent with Bash.
homepage: local
metadata: {"version":"1.0.0","updated":"2026-06-22","author":"gwendall","openclaw":{"requires":{"bins":["curl","python3"]},"emoji":"mag"}}
---

# wallet-analysis - On-chain relationship analysis (EVM)

Given **an address** (EVM, Ethereum mainnet or an L2), produce:

1. **Where the wallet comes from**: who funded it first (genesis funding), and going up the chain, the ultimate origin of the funds (often a CEX exchange = KYC'd person).
2. **All EOA counterparties** (real wallets/people) vs **contracts** (protocols, marketplaces).
3. **The excluded spam**: dust tokens, airdrops, address-poisoning.
4. **The clustering**: which wallets probably belong to the **same owner** and why.

Everything is doable **without an API key**. The core work lives in `scripts/analyze_wallet.py`; this document explains the method, the tools, and the pitfalls so you can do it by hand or interpret/extend the script.

## TL;DR - the fast path

```bash
# 1 command: full history + classification + clustering
python3 scripts/analyze_wallet.py 0xADDRESS --chain 1 --json /tmp/wallet.json
```

Then, to **confirm the labels** of suspicious EOAs (exchanges) and unlabeled contracts, run a `WebFetch` on `https://etherscan.io/address/<addr>` (the public name tag is in the page). This is the one step the script does not do on its own.

Then write the report: profile, funder, EOA table, contracts, spam, clustering conclusion. See **Final report** below.

## The tools / data sources (and which ones work)

| Need | Source that works WITHOUT a key | Notes |
|---|---|---|
| Full history (txlist, internal, ERC20, NFT) | **Routescan** (Etherscan-compatible API) | `https://api.routescan.io/v2/network/mainnet/evm/{chainId}/etherscan/api?module=account&action=...` Most reliable, multi-chain. |
| Same, fallback | **Blockscout v1** | `https://eth.blockscout.com/api?module=account&action=txlist&address=...` Works. **BUT** the v2 API (`/api/v2/addresses/...`) often returns **0 / incomplete** - do NOT rely on it for the counters. |
| EOA vs contract, nonce, balance | **Public RPC** | POST JSON-RPC to `https://ethereum-rpc.publicnode.com` or `https://eth.drpc.org`. `eth_getCode` (0x = EOA), `eth_getTransactionCount` (nonce = number of outgoing tx), `eth_getBalance`. |
| Labels (exchange, contract, entity) | **WebFetch on Etherscan** | `https://etherscan.io/address/<addr>` -> the "public name tag" is in the page. Only no-key method to name "Binance 10", "Kraken 4", etc. |
| Token logos / scam flag | Blockscout v2 `/api/v2/addresses/{a}` | `is_scam`, `has_token_transfers` fields. Useful as a complement. |

**Do NOT use** (they fail or require a key): Etherscan API V1 (deprecated), Etherscan V2 (key required), `rpc.ankr.com/eth` (key), `eth.llamarpc.com` and `cloudflare-eth.com` (unstable, 521/errors).

### Routescan multi-chain

`{chainId}`: `1`=Ethereum, `8453`=Base, `42161`=Arbitrum, `10`=Optimism, `137`=Polygon, `56`=BSC, `43114`=Avalanche. The script handles these chains (`--chain` flag).

## The method, step by step (to do it by hand)

### Step 0 - base profile (RPC)
```bash
ADDR="0x..."
RPC="https://ethereum-rpc.publicnode.com"
# EOA? (0x = yes)
curl -s -X POST $RPC -H "Content-Type: application/json" \
  --data "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getCode\",\"params\":[\"$ADDR\",\"latest\"],\"id\":1}"
# nonce (number of outgoing tx - 0 = never sent a tx)
curl -s -X POST $RPC -H "Content-Type: application/json" \
  --data "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getTransactionCount\",\"params\":[\"$ADDR\",\"latest\"],\"id\":1}"
# balance
curl -s -X POST $RPC -H "Content-Type: application/json" \
  --data "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"$ADDR\",\"latest\"],\"id\":1}"
```
The **nonce** is a key sanity-check: if an indexer says "0 transactions" but nonce > 0, the indexer is incomplete (happened with Blockscout v2) - switch source.

### Step 1 - full history (Routescan)
```bash
BASE="https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api"
for ACTION in txlist txlistinternal tokentx tokennfttx; do
  curl -s "$BASE?module=account&action=$ACTION&address=$ADDR&startblock=0&endblock=99999999&sort=asc&offset=10000" \
    -o "/tmp/$ACTION.json"
done
```
- `txlist` = native tx (ETH + contract calls signed by the address)
- `txlistinternal` = ETH received/sent **via a contract** (e.g. DEX withdrawal, disperse). Important: a wallet can have 0 incoming native tx but be funded by an internal tx.
- `tokentx` = ERC-20 transfers (often spam)
- `tokennfttx` = ERC-721/1155 transfers

### Step 2 - find the FUNDER (who funded it)
The funder = **the first incoming ETH transfer** (`value > 0`, `to == addr`), before any wallet activity, sorting `txlist + txlistinternal` by ascending block. This is the classic "genesis funding" heuristic: the first address to send ETH to a fresh wallet is almost always its creator/parent.

### Step 3 - enumerate + classify the counterparties
For each address on the other side (from/to), aggregate: ETH in/out, number of tx, first/last interaction, methods called. Then classify each one **EOA vs contract** with `eth_getCode` (1 RPC call per address). Contracts = protocols (to exclude from the "which wallets/people" question); EOAs = the real wallets to analyze.

### Step 4 - label
- Known contracts: WETH, Seaport/OpenSea, Uniswap, ParaSwap... (see `references/known-addresses.md`).
- EOA with nonce **> 100,000** = automated hot wallet (CEX / bot / market-maker), **never the owner**.
- To attach a name (Binance 10, Kraken 4, a specific NFT contract): `WebFetch https://etherscan.io/address/<addr>`.

### Step 5 - trace the origin chain
Take the funder (step 2) and repeat step 2 **on it**: who funded it? Often within 1-2 hops you land on an exchange hot wallet (huge nonce). Confirm "Binance/Kraken/Coinbase" via WebFetch Etherscan. Conclusion: "the funds come, at the root, from such-and-such exchange(s)" = the person has a KYC'd account there.

### Step 6 - filter out spam (see dedicated section)

### Step 7 - clustering (see dedicated section)

## Spam detection (to EXCLUDE)

Token/NFT spam signals, not to be counted as real relationships:

- **Same symbol across several different contracts**: e.g. 10 "FEET" / "Feet Coin" / "feetpix" contracts = airdrop spam. (The script flags this automatically via `likely_spam_symbols`.)
- **Token received but never used/sent back** (`n_out == 0`) from an unknown contract = dust airdrop.
- **Zero-value transfers** and **address-poisoning**: an address that looks like (same first 4 / last 4 hex) a legitimate counterparty, sending you a 0 transfer to pollute your history and trip you up on copy-paste. Always compare the **full** address.
- **NFTs mass-minted/airdropped** by unknown contracts.

What is **NOT** spam and does count: NFT/token transfers **in both directions** with the same EOA (strong clustering signal, see below), marketplace buys/sells, DEX swaps.

## Clustering - "same owner?" (the heart of the analysis)

Heuristics, from strongest to weakest:

1. **Genesis funding**: X is the first address to have funded the wallet -> X is very likely the parent wallet / same owner.
2. **Bidirectional NFT/token transfers**: you don't send a valuable NFT to a stranger. Token/NFT sent AND received with the same EOA -> almost certainly same owner (or very close).
3. **Bidirectional ETH flows + near-equal round-trips**: receives 4 ETH, sends 4.1 ETH back a few days later to the same address = treasury management by a single operator across their wallets.
4. **"Funded then idle" downstream**: a wallet that received ETH from the subject **and nothing else** (1 tx, never re-emitted) = disposable/secondary wallet of the same owner.
5. **Common funding source**: two wallets funded by the **same** exchange deposit address (a dedicated, non-shared deposit address) -> same CEX account -> same person.
6. **Relay / pass-through**: receives X, sends ~X immediately (same block) to a 3rd address. The middle wallet is a hop (often toward a swap like SimpleSwap/ChangeNOW to break the link). Follow the final destination.

**False positives to avoid**: an EOA with nonce > 100k (CEX/bot) is NOT the owner even with bidirectional flows (exchanges send ETH back). A one-off counterparty from an NFT sale may just be an external buyer. Always distinguish "same owner" from "mere counterparty".

## Technical pitfalls (learned the hard way, worth knowing)

- **zsh does NOT word-split** an unquoted `$VAR`. A loop `for A in $LIST` treats everything as a single word. -> put the addresses in **Python**, or a zsh **array**, or `${=LIST}`.
- **urllib -> 403** on drpc/blockscout/etherscan without a `User-Agent`. Always add `headers={"User-Agent":"Mozilla/5.0"}`.
- **Blockscout API v2** (`/api/v2/addresses/...`) can return `transactions_count: 0` and empty lists for an otherwise active address. Never conclude "empty wallet" on that basis alone: cross-check with the **RPC nonce** and **Routescan**.
- **Etherscan API V1** returns "deprecated, switch to V2"; **V2** requires a key. -> go through **Routescan** (compatible) or **WebFetch** on Etherscan pages.
- **Routescan pagination**: `offset` caps out (~10000). For a very active wallet, paginate (`page=1,2,...`) or bound with `startblock/endblock`.
- **Internal txs have no `input` field**: that's how you detect funding coming from a contract (CEX withdrawal via contract, disperse, etc.).

## The script

`scripts/analyze_wallet.py` chains steps 0-7 automatically:

```bash
python3 scripts/analyze_wallet.py 0xADDRESS              # Ethereum mainnet
python3 scripts/analyze_wallet.py 0xADDRESS --chain 8453 # Base
python3 scripts/analyze_wallet.py 0xADDRESS --json out.json
```

Output: profile, initial funder, counterparty EOAs (with exchange flag), labeled contracts, spam symbols, and a **clustering** block with per-address signals. `--json` lets you post-process.

**What the script does not do** (for the agent to do afterward):
- Confirm the exact labels via `WebFetch` on Etherscan (exchanges, specific NFT contracts).
- Recursively trace the origin chain (re-run the script on the funder's address).
- Judge the final clustering (the script gives the signals; the human/agent decides "same owner" vs "counterparty").

Extending the labels: add confirmed addresses to `references/known-addresses.md` **and** to the `KNOWN_CONTRACTS` / `KNOWN_CEX` dicts in the script.

## Final report - recommended structure

1. **One-sentence conclusion** (e.g. "secondary wallet of a single owner, funded by hub X, funds sourced from Binance/Kraken").
2. **ID card**: type, balance, nonce, activity period, usage profile (NFT/DeFi/...).
3. **Where it comes from / who funded it**: genesis funding + chain traced up to the exchange.
4. **Table of counterparty EOAs**: address, relationship, verdict (same owner / external counterparty / relay / exchange).
5. **Contracts** (listed separately - these are protocols, not people).
6. **The key link (clustering)**: which wallets = same owner and the 2-3 proofs.
7. **Excluded spam**: what was set aside and why.

## Limits / honesty

- Genesis-funding and clustering are **probabilistic heuristics**, not proof. Phrase as "probable / near-certain / confirmed", never as absolute certainty.
- **Mixers** (Tornado), **bridges**, and **instant swaps** deliberately break traceability: flag when the trail stops there.
- Etherscan labels can be incomplete or stale. A huge nonce remains the most robust signal for "automated service".
- This skill is meant for **defensive analysis / due diligence / curiosity** on public on-chain data. Not for targeted deanonymization of individuals.
