"""cambc CLI wrapper with retry on the platform's rate limit (HTTP 429 / "busy") and outages (HTTP 503 "unavailable").

The platform answers "retry after N seconds"; we sleep exactly that (plus jitter) instead of a growing backoff.
A process-wide minimum gap between calls (LIVE_MIN_GAP seconds, default 0.35) keeps parallel workers polite."""
import os, random, re, subprocess, threading, time

_lock = threading.Lock()
_last = [0.0]
MIN_GAP = float(os.environ.get("LIVE_MIN_GAP", "0.35"))


def _pace():
    with _lock:
        now = time.time()
        wait = _last[0] + MIN_GAP - now
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()


def run(args, retries=40):
    """Run `cambc *args`; retry while the public API is busy. Returns (rc, stdout, stderr)."""
    for attempt in range(retries + 1):
        _pace()
        r = subprocess.run(["cambc"] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
        msg = (r.stderr or "") + (r.stdout if r.returncode else "")
        low = msg.lower()
        busy = r.returncode != 0 and ("429" in msg or "503" in msg or "busy" in low or "rate limit" in low or "unavailable" in low)
        if not busy or attempt == retries:
            return r.returncode, r.stdout, r.stderr
        m = re.search(r"retry after (\d+(?:\.\d+)?) second", msg)
        wait = float(m.group(1)) if m else 2.0
        time.sleep(wait + random.random() * 0.5)
    return r.returncode, r.stdout, r.stderr
