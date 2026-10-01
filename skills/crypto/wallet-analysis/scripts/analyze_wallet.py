#!/usr/bin/env python3
"""
analyze_wallet.py - On-chain relationship analysis of an EVM EOA address.

No API key required. Sources:
  - Routescan (Etherscan-compatible API, multi-chain, keyless) -> full history
  - Public RPCs (publicnode / drpc) -> code, nonce, balance, EOA/contract classification

What the script produces:
  - Base profile (EOA/contract, balance, nonce, age, activity period)
  - The initial FUNDER (first incoming ETH transfer, before any activity)
  - All counterparties, classified EOA vs CONTRACT
  - Spam detection (dust tokens, same symbol across several contracts, airdrops)
  - Clustering heuristics (probable same owner)
  - Flagging of exchange hot wallets (huge nonce) to confirm via Etherscan

Usage:
  python3 analyze_wallet.py 0xADDRESS [--chain 1] [--json out.json] [--max-spam 3]

Supported chains (Routescan): 1=eth, 8453=base, 42161=arbitrum, 10=optimism,
  137=polygon, 56=bsc, 43114=avalanche. Default: 1 (Ethereum mainnet).

NB: the script FLAGS probable exchanges (nonce > 100k) but does not know all
labels. To confirm the identity ("Binance 10", "Kraken 4"...), the agent must
run a WebFetch on https://etherscan.io/address/<addr>
(the public name tag appears in the page). See SKILL.md.
"""
import sys, json, time, argparse, urllib.request, urllib.error

# ---------- endpoints ----------
ROUTESCAN = "https://api.routescan.io/v2/network/mainnet/evm/{chain}/etherscan/api"
RPCS = {
    1:     ["https://ethereum-rpc.publicnode.com", "https://eth.drpc.org"],
    8453:  ["https://base-rpc.publicnode.com", "https://base.drpc.org"],
    42161: ["https://arbitrum-one-rpc.publicnode.com", "https://arbitrum.drpc.org"],
    10:    ["https://optimism-rpc.publicnode.com", "https://optimism.drpc.org"],
    137:   ["https://polygon-bor-rpc.publicnode.com", "https://polygon.drpc.org"],
    56:    ["https://bsc-rpc.publicnode.com", "https://bsc.drpc.org"],
    43114: ["https://avalanche-c-chain-rpc.publicnode.com", "https://avalanche.drpc.org"],
}
UA = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

# ---------- known labels (extend via references/known-addresses.md) ----------
KNOWN_CONTRACTS = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH (Wrapped Ether)",
    "0xdef171fe48cf0115b1d80b88dc8eab59176fee57": "ParaSwap: Augustus Swapper (DEX)",
    "0x00000000006c3852cbef3e08e8df289169ede581": "OpenSea: Seaport 1.1 (NFT marketplace)",
    "0x00000000000000adc04c56bf30ac9d3c0aaf14dc": "OpenSea: Seaport 1.5 (NFT marketplace)",
    "0x7f268357a8c2552623316e2562d90e642bb538e5": "OpenSea: Wyvern Exchange v2",
    "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch v5 Router (DEX)",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2: Router",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3: Router",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "Uniswap Universal Router",
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap Universal Router",
}
# known CEX hot wallets (sample; the nonce>100k detection covers the rest)
KNOWN_CEX = {
    "0x85b931a32a0725be14285b66f1a22178c672d69b": "Binance 10",
    "0x564286362092d8e7936f0549571a803b203aaced": "Binance 3",
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken 4",
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance 14",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance 15",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance 16",
    "0x9696f59e4d72e237be84ffd425dcad154bf96976": "Binance 18",
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase 1",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase 2",
    "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": "Coinbase 3",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": "Coinbase 10",
    "0xe93381fb4c4f14bda253907b18fad305d799241a": "Huobi",
    "0xfa52274dd61e1643d2205169732f29114bc240b3": "Kraken 1",
}

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def rpc(chain, method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    for node in RPCS.get(chain, RPCS[1]):
        try:
            req = urllib.request.Request(node, data=body, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read().decode())
                if "result" in d:
                    return d["result"]
        except Exception:
            continue
    return None

def routescan(chain, action, address, extra=""):
    url = (ROUTESCAN.format(chain=chain)
           + f"?module=account&action={action}&address={address}"
             f"&startblock=0&endblock=99999999&sort=asc&page=1&offset=10000{extra}")
    try:
        d = http_get(url)
        res = d.get("result")
        return res if isinstance(res, list) else []
    except Exception:
        return []

# ---------- helpers ----------
def to_eth(wei):
    try: return int(wei) / 1e18
    except Exception: return 0.0

def fdate(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts)))

def is_eoa(chain, addr):
    code = rpc(chain, "eth_getCode", [addr, "latest"])
    return code == "0x" or code == "0x0" or code is None

def label_for(addr, is_contract, sender_nonce=None):
    a = addr.lower()
    if a in KNOWN_CONTRACTS: return KNOWN_CONTRACTS[a]
    if a in KNOWN_CEX:       return KNOWN_CEX[a] + " (CEX hot wallet)"
    if is_contract is True:  return "contract (unlabeled)"
    return "EOA"

# ---------- analysis ----------
def analyze(address, chain, max_spam):
    addr = address.lower()
    out = {"address": address, "chain": chain}

    # base profile
    code = rpc(chain, "eth_getCode", [addr, "latest"])
    out["is_contract"] = not (code in ("0x", "0x0", None))
    nonce_hex = rpc(chain, "eth_getTransactionCount", [addr, "latest"])
    out["nonce_outgoing_tx"] = int(nonce_hex, 16) if nonce_hex else 0
    bal_hex = rpc(chain, "eth_getBalance", [addr, "latest"])
    out["balance_eth"] = to_eth(int(bal_hex, 16)) if bal_hex else 0.0

    normal   = routescan(chain, "txlist", addr)
    internal = routescan(chain, "txlistinternal", addr)
    erc20    = routescan(chain, "tokentx", addr)
    nft      = routescan(chain, "tokennfttx", addr)
    out["counts"] = {"normal": len(normal), "internal": len(internal),
                     "erc20": len(erc20), "nft": len(nft)}

    all_value_in = [t for t in (normal + internal)
                    if (t.get("to") or "").lower() == addr and int(t.get("value", 0)) > 0
                    and t.get("isError", "0") != "1"]
    all_value_in.sort(key=lambda t: (int(t["blockNumber"]), int(t.get("timeStamp", 0))))

    # funder = first incoming ETH transfer
    if all_value_in:
        f = all_value_in[0]
        out["funder"] = {
            "address": f["from"],
            "value_eth": to_eth(f["value"]),
            "date": fdate(f["timeStamp"]),
            "hash": f.get("hash"),
            "via_internal_tx": "input" not in f,  # internal txs have no input field
        }
    else:
        out["funder"] = None

    # activity period
    stamps = [int(t["timeStamp"]) for t in normal if t.get("timeStamp")]
    if stamps:
        out["first_activity"] = fdate(min(stamps))
        out["last_activity"]  = fdate(max(stamps))

    # ---------- counterparties ----------
    cps = {}  # addr -> stats
    def touch(cp, direction, value, ts, method):
        cp = cp.lower()
        if not cp or cp == addr or cp == "0x0000000000000000000000000000000000000000":
            return
        d = cps.setdefault(cp, {"in_eth": 0.0, "out_eth": 0.0, "n_in": 0, "n_out": 0,
                                "first_ts": ts, "last_ts": ts, "methods": set()})
        if direction == "in":
            d["in_eth"] += to_eth(value); d["n_in"] += 1
        else:
            d["out_eth"] += to_eth(value); d["n_out"] += 1
        d["first_ts"] = min(d["first_ts"], ts); d["last_ts"] = max(d["last_ts"], ts)
        if method: d["methods"].add(method)

    for t in normal:
        ts = int(t.get("timeStamp", 0))
        method = (t.get("functionName") or t.get("methodId") or "")[:40]
        if (t.get("to") or "").lower() == addr:
            touch(t["from"], "in", t.get("value", 0), ts, method)
        elif (t.get("from") or "").lower() == addr:
            touch(t.get("to") or "", "out", t.get("value", 0), ts, method)
    for t in internal:
        ts = int(t.get("timeStamp", 0))
        if (t.get("to") or "").lower() == addr:
            touch(t.get("from") or "", "in", t.get("value", 0), ts, "internal")
        elif (t.get("from") or "").lower() == addr:
            touch(t.get("to") or "", "out", t.get("value", 0), ts, "internal")

    # EOA/contract classification (1 RPC call per counterparty)
    eoas, contracts = [], []
    for cp, d in cps.items():
        contract = not is_eoa(chain, cp)
        nonce_hex = rpc(chain, "eth_getTransactionCount", [cp, "latest"])
        cp_nonce = int(nonce_hex, 16) if nonce_hex else 0
        likely_cex = (not contract) and cp_nonce > 100000
        rec = {
            "address": cp,
            "type": "CONTRACT" if contract else "EOA",
            "label": label_for(cp, contract),
            "in_eth": round(d["in_eth"], 6),
            "out_eth": round(d["out_eth"], 6),
            "n_tx": d["n_in"] + d["n_out"],
            "first": fdate(d["first_ts"]), "last": fdate(d["last_ts"]),
            "methods": sorted(d["methods"])[:6],
            "nonce": cp_nonce,
            "likely_exchange": likely_cex,
            "bidirectional": d["n_in"] > 0 and d["n_out"] > 0,
        }
        if cp.lower() in KNOWN_CEX:
            rec["label"] = KNOWN_CEX[cp.lower()] + " (CEX hot wallet)"
            rec["likely_exchange"] = True
        (contracts if contract else eoas).append(rec)

    eoas.sort(key=lambda r: r["n_tx"], reverse=True)
    contracts.sort(key=lambda r: r["n_tx"], reverse=True)
    out["eoa_counterparties"] = eoas
    out["contract_counterparties"] = contracts

    # ---------- spam tokens ----------
    sym_contracts = {}  # symbol -> set(contract)
    for t in erc20:
        sym = (t.get("tokenSymbol") or "?").lower()
        sym_contracts.setdefault(sym, set()).add((t.get("contractAddress") or "").lower())
    spam_symbols = {s for s, c in sym_contracts.items() if len(c) > 1}  # same symbol, N contracts
    token_summary = {}
    for t in erc20:
        sym = t.get("tokenSymbol") or "?"
        c = (t.get("contractAddress") or "").lower()
        incoming = (t.get("to") or "").lower() == addr
        rec = token_summary.setdefault(c, {"symbol": sym, "name": t.get("tokenName"),
                                           "n_in": 0, "n_out": 0,
                                           "spam_flag": sym.lower() in spam_symbols})
        rec["n_in" if incoming else "n_out"] += 1
    # tokens received but never sent back/used = suspicious dust
    for c, r in token_summary.items():
        if r["n_out"] == 0 and r["n_in"] >= 1 and c not in KNOWN_CONTRACTS:
            r.setdefault("spam_flag", False)
            r["dust_only_inbound"] = True
    out["tokens"] = sorted(token_summary.values(), key=lambda r: r["n_in"] + r["n_out"], reverse=True)
    out["likely_spam_symbols"] = sorted(spam_symbols)

    # ---------- clustering heuristics ----------
    cluster = []
    funder_addr = out["funder"]["address"].lower() if out["funder"] else None
    for r in eoas:
        signals = []
        a = r["address"].lower()
        if a == funder_addr:
            signals.append("INITIAL FUNDER (genesis funding)")
        if r["bidirectional"]:
            signals.append("bidirectional ETH flows")
        if r["in_eth"] > 0 and r["out_eth"] > 0 and abs(r["in_eth"] - r["out_eth"]) / max(r["in_eth"], r["out_eth"]) < 0.1:
            signals.append("near-equal round-trip")
        if r["likely_exchange"]:
            signals.append("high-frequency address nonce>100k (CEX/bot/market-maker, NOT the owner) - confirm the label via Etherscan")
        if r["n_tx"] == 1 and r["out_eth"] == 0 and r["in_eth"] > 0:
            signals.append("received then stayed inactive (probable downstream wallet)")
        if signals:
            cluster.append({"address": r["address"], "type": r["type"],
                            "label": r["label"], "signals": signals})
    out["clustering"] = cluster
    return out

def print_report(o):
    A = o["address"]
    print("=" * 90)
    print(f"WALLET ANALYSIS  {A}   (chain {o['chain']})")
    print("=" * 90)
    print(f"Type            : {'CONTRACT' if o['is_contract'] else 'EOA'}")
    print(f"Balance         : {o['balance_eth']:.6f} (native token)")
    print(f"Outgoing tx     : {o['nonce_outgoing_tx']} (nonce)")
    print(f"Activity        : {o.get('first_activity','?')}  ->  {o.get('last_activity','?')}")
    print(f"Indexed volumes : {o['counts']}")
    print()
    if o["funder"]:
        f = o["funder"]
        via = " (via internal tx / contract)" if f.get("via_internal_tx") else ""
        print(f"INITIAL FUNDER : {f['address']}")
        print(f"   {f['value_eth']:.6f} on {f['date']}{via}")
    else:
        print("INITIAL FUNDER : no incoming ETH transfer found")
    print()
    print(f"--- COUNTERPARTY EOAs ({len(o['eoa_counterparties'])}) ---")
    for r in o["eoa_counterparties"]:
        flag = "  <-- EXCHANGE?" if r["likely_exchange"] else ""
        print(f"  {r['address']}  in={r['in_eth']:.4f} out={r['out_eth']:.4f} "
              f"tx={r['n_tx']} {r['label']}{flag}")
    print()
    print(f"--- COUNTERPARTY CONTRACTS ({len(o['contract_counterparties'])}) ---")
    for r in o["contract_counterparties"]:
        print(f"  {r['address']}  tx={r['n_tx']}  {r['label']}")
    print()
    if o["likely_spam_symbols"]:
        print(f"Probable SPAM (same symbol across several contracts) : {o['likely_spam_symbols']}")
    print()
    print("--- CLUSTERING (links to other wallets) ---")
    if not o["clustering"]:
        print("  no strong signal")
    for c in o["clustering"]:
        print(f"  {c['address']} [{c['type']}] {c['label']}")
        for s in c["signals"]:
            print(f"     - {s}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("address")
    ap.add_argument("--chain", type=int, default=1)
    ap.add_argument("--json", default=None, help="write the JSON report to this file")
    ap.add_argument("--max-spam", type=int, default=3)
    args = ap.parse_args()
    if not args.address.lower().startswith("0x") or len(args.address) != 42:
        print("Invalid address", file=sys.stderr); sys.exit(1)
    o = analyze(args.address, args.chain, args.max_spam)
    print_report(o)
    if args.json:
        # set -> list for serialization
        json.dump(o, open(args.json, "w"), indent=2, default=lambda x: list(x) if isinstance(x, set) else str(x))
        print(f"\nJSON written to {args.json}")

if __name__ == "__main__":
    main()
