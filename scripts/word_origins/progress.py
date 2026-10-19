import sys
import time
from datetime import datetime, timedelta

BAR_WIDTH = 24
FILLED, EMPTY = "#", "-"


def clock(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))


class Progress:
    def __init__(self, label: str, total: int, stream=sys.stdout):
        self.label, self.total, self.done = label, max(total, 1), 0
        self.stream, self.started = stream, time.monotonic()
        self.interactive = stream.isatty()

    def estimate(self) -> str:
        if not self.done:
            return "estimating"
        elapsed = time.monotonic() - self.started
        remaining = elapsed / self.done * (self.total - self.done)
        return f"ETA {clock(remaining)} (done about {(datetime.now() + timedelta(seconds=remaining)):%H:%M:%S})"

    def line(self, note: str) -> str:
        share = min(self.done / self.total, 1)
        bar = FILLED * int(share * BAR_WIDTH) + EMPTY * (BAR_WIDTH - int(share * BAR_WIDTH))
        elapsed = clock(time.monotonic() - self.started)
        return f"[{self.label}] [{bar}] {share:4.0%} {self.done}/{self.total} | elapsed {elapsed} | {self.estimate()} | {note}"

    def show(self, note: str) -> None:
        text = self.line(note)
        self.stream.write(("\r\033[K" + text) if self.interactive else text + "\n")
        self.stream.flush()

    def advance(self, note: str, amount: int = 1) -> None:
        self.done += amount
        self.show(note)

    def message(self, note: str) -> None:
        self.show(note)

    def finish(self, note: str = "complete") -> None:
        if self.done < self.total:
            self.done = self.total
            self.show(note)
        self.stream.write("\n")
        self.stream.flush()
