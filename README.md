# Confirmed Dip — BTC Race

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/arizkis/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/arizkis/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A deterministic, long-only cbBTC paper-trading bot built for make.fun's 24-hour
BTC race. It stays in cash until a substantial dip begins to recover, then
trades one position per episode. No network, clock, external model or runtime
dependencies; the only vendored source is the kit's unchanged Python SDK.

## Strategy

| Rule | Setting |
| --- | --- |
| Dip | Close at least 1.25% below the highest close seen so far |
| Confirmation | Close above both open and previous close; green body at least 1 bp; Wilder RSI(14) below 40 |
| Entry | 100% of available cash, one position; no averaging |
| Re-entry | A new session closing high must re-arm the dip signal |
| Profit exit | Close at least 1.25% above the actual buy fill price |
| Loss exit | Close at least 0.50% below the actual buy fill price |
| Time exit | 300 minutes after the buy fills |
| Orders | Fill at the following open; slippage cap 100 bps |
| Endgame | Signal entries stop after batch 1380; no orders on final batch 1439 |

If no buy has filled by batch 1380, the bot makes one eligibility buy with
25% of cash, with the same exits. It retries on subsequent observed bars if
that buy is rejected, until a buy fills or the final batch arrives. The
replay liquidates any remaining position at the last close. Rejected exits
remain pending and are retried on subsequent observed bars. Missing bars
do not update price history or indicators.

## Validation

The entry was replayed as an actual Python subprocess through the kit's
unchanged `BarsEngine`, including full hello/batch/reply/done messages,
integer fees, impact, slippage, next-open execution and final liquidation.
Two independent executions produced byte-identical complete action logs.

Local dev-window result: **+16.142720 USDC**, four filled orders (two round
trips), **0.595187%** maximum drawdown, **1.616656 USDC** explicit fees.
With the engine's explicit fee doubled: **+14.521717 USDC**. These are local
measurements on the published dev window, not official scores or forecasts.
Docker is unavailable on the build machine, so `grade-local --driver docker`
cannot run here; the official server grade remains the authority.

Flat, steadily rising (+3%) and steadily falling (-6%) synthetic windows
were also checked, including absent bars at the eligibility decision and
fill, and a run of 28 missing bars. On a flat window the required 25% trade
loses about **0.425 USDC**, including execution costs and final liquidation.

This strategy can miss a sustained rally and can lose money during a
continuing decline. Stops are decisions for the next open, not guaranteed
execution prices. Two profitable dev trades do not establish future edge
or a probability of winning the race.

## Run it

Python 3.13, standard library only:

```sh
python3 -P -s main.py
```

Feed newline-delimited `agent-fun/bars-replay/v1` messages on stdin. Stdout
contains exactly one JSON reply per batch and no diagnostic text.

---

<sub>Entered on [make.fun](https://make.fun/?ref=8kbmacyg&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
