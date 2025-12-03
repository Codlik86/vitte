import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.utils.async_helpers import ensure_async_iter  # noqa: E402


async def main():
    session_iter = ensure_async_iter([1, 2, 3])
    collected = []
    async for item in session_iter:
        collected.append(item)
    if collected != [1, 2, 3]:
        raise SystemExit(f"ERROR: unexpected collected items: {collected}")
    print("OK: session_iter consumed without TypeError:", collected)


if __name__ == "__main__":
    asyncio.run(main())
