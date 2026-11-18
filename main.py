"""Confirmed-dip, episode-limited strategy for agent-fun/bars-replay/v1.

Decisions use only the current batch and earlier bars. Orders fill at the
next open; exits refer to the reported fill, never an assumed close fill.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars


SYMBOL = "CBBTC"
BPS = 10_000
RSI_PERIOD = 14
DIP_BPS = 125
TAKE_PROFIT_BPS = 125
STOP_LOSS_BPS = 50
MAX_HOLD_BARS = 300
ENTRY_CUTOFF = 1380
FINAL_BAR = 1439
MAX_SLIPPAGE_BPS = 100


class ConfirmedDip:
    def __init__(self):
        self.previous_close = None
        self.running_high = 0
        self.armed = True
        self.changes = 0
        self.gain = 0.0
        self.loss = 0.0
        self.entry_price = None
        self.entry_seq = None
        self.buy_fills = 0
        self.last_exit_seq = -1
        self.exit_pending = False

    def update_rsi(self, close):
        if self.previous_close is None:
            self.previous_close = close
            return None
        change = close - self.previous_close
        self.previous_close = close
        up, down = max(change, 0), max(-change, 0)
        self.changes += 1
        if self.changes <= RSI_PERIOD:
            self.gain += up
            self.loss += down
            if self.changes < RSI_PERIOD:
                return None
            self.gain /= RSI_PERIOD
            self.loss /= RSI_PERIOD
        else:
            self.gain = (self.gain * (RSI_PERIOD - 1) + up) / RSI_PERIOD
            self.loss = (self.loss * (RSI_PERIOD - 1) + down) / RSI_PERIOD
        if self.gain + self.loss == 0:
            return 50.0
        return 100.0 * self.gain / (self.gain + self.loss)

    def order(self, state, side, amount):
        key = "notional_quote_units" if side == "buy" else "qty"
        return [{"side": side, "symbol": SYMBOL, key: amount,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]

    def on_batch(self, state, batch):
        seq = state.seq - state.warmup_bars
        position = state.positions.get(SYMBOL)
        for fill in batch["fills"]:
            if (fill.get("symbol") != SYMBOL or fill["status"] != "filled"
                    or fill["client_id"].startswith("_")):
                continue
            if fill["side"] == "buy":
                self.buy_fills += 1
                self.entry_price = int(fill["price"])
                self.entry_seq = seq
            elif position is None:
                self.entry_price = None
                self.entry_seq = None
                self.last_exit_seq = seq
                self.exit_pending = False

        bar = next((b for b in batch["bars"] if b["symbol"] == SYMBOL), None)
        if bar is None:
            return []
        close, opened = int(bar["c"]), int(bar["o"])
        previous = self.previous_close
        rsi = self.update_rsi(close)
        if close > self.running_high:
            self.running_high = close
            self.armed = True
        if state.warming_up or seq >= FINAL_BAR:
            return []

        if position is not None:
            # Account state is authoritative; use the close only if a fill
            # price was unexpectedly absent from the reported resolutions.
            if self.entry_price is None:
                self.entry_price = close
                self.entry_seq = seq
            profit = close * BPS >= self.entry_price * (BPS + TAKE_PROFIT_BPS)
            stop = close * BPS <= self.entry_price * (BPS - STOP_LOSS_BPS)
            expired = seq - self.entry_seq >= MAX_HOLD_BARS
            # A no_bar/max_slippage rejection must not cancel a triggered
            # exit. Reissue it on subsequent observed bars until filled.
            self.exit_pending = self.exit_pending or profit or stop or expired
            if self.exit_pending:
                return self.order(state, "sell", position.qty)
            return []

        if seq == self.last_exit_seq:
            return []
        confirmed = (seq <= ENTRY_CUTOFF and self.armed
                     and rsi is not None and rsi < 40.0
                     and close * BPS <= self.running_high * (BPS - DIP_BPS)
                     and previous is not None and close > previous
                     and close > opened and (close - opened) * BPS >= close)
        if confirmed:
            self.armed = False
            amount = min(state.cash, state.weight_room(SYMBOL))
        elif seq >= ENTRY_CUTOFF and self.buy_fills == 0:
            # The one eligibility trade is retried if its open was absent
            # or too far away. Stop retries immediately after a real fill.
            amount = state.cash // 4
        else:
            return []
        if amount < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        return self.order(state, "buy", amount)


def on_batch(state, batch):
    if not hasattr(state, "strategy"):
        state.strategy = ConfirmedDip()
    return state.strategy.on_batch(state, batch)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
