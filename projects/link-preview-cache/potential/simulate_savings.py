#!/usr/bin/env python3
"""Honest, explicit-assumptions simulation of why a flat $0.003 price is
sustainable here, and how much agents collectively save vs. paying $0.01
per call (link-preview-api's price) for the same data.

This is NOT observed traffic - there is none yet, this product doesn't
exist yet. It's a model, with its one real assumption stated up front:
requests for shareable web content follow a Zipf-ish "some URLs get looked
up a lot, most get looked up rarely" distribution - the same long-tail
pattern documented in web-traffic and content-sharing studies generally.
Change ZIPF_SKEW / POOL_SIZE / the volume list below and re-run to see how
sensitive the numbers are to that assumption.

Run: python simulate_savings.py
"""

from __future__ import annotations

import random

BASELINE_PRICE_USD = 0.01  # link-preview-api's flat price, no caching
CACHE_PRICE_USD = 0.003  # this project's flat price
TTL_SECONDS = 21_600  # 6h, matches CACHE_TTL_SECONDS default
SECONDS_PER_DAY = 86_400

POOL_SIZE = 2_000  # distinct URLs that could plausibly be requested in a day
ZIPF_SKEW = 1.1  # higher = more concentrated on a few popular URLs
DAILY_VOLUMES = [100, 1_000, 10_000, 100_000]
SEED = 7  # reproducible run


def simulate(requests_per_day: int, *, seed: int = SEED) -> dict:
    rng = random.Random(seed)
    urls = [f"url_{i}" for i in range(POOL_SIZE)]
    weights = [1 / (rank**ZIPF_SKEW) for rank in range(1, POOL_SIZE + 1)]

    last_fetched_at: dict[str, float] = {}
    hits = 0

    for i in range(requests_per_day):
        # Spread requests evenly across a 24h window - denser at higher
        # daily volume, which is exactly what should make cache hits more
        # likely (a popular URL gets asked about again sooner).
        now = i * (SECONDS_PER_DAY / requests_per_day)
        url = rng.choices(urls, weights=weights, k=1)[0]

        seen_at = last_fetched_at.get(url)
        if seen_at is not None and (now - seen_at) <= TTL_SECONDS:
            hits += 1
        else:
            last_fetched_at[url] = now

    hit_rate = hits / requests_per_day
    baseline_cost = requests_per_day * BASELINE_PRICE_USD
    our_cost = requests_per_day * CACHE_PRICE_USD  # flat price regardless of hit/miss
    savings = baseline_cost - our_cost

    return {
        "requests_per_day": requests_per_day,
        "cache_hit_rate": hit_rate,
        "baseline_cost_usd": baseline_cost,
        "our_cost_usd": our_cost,
        "agent_savings_usd": savings,
        "agent_savings_pct": (savings / baseline_cost) * 100,
        # What WE actually spend effort/compute on: only the misses do a
        # real fetch+parse. This is the number that makes the flat lower
        # price sustainable, not just a promotional discount.
        "our_real_fetches": requests_per_day - hits,
    }


def main() -> None:
    print(f"Assumptions: pool={POOL_SIZE} URLs, Zipf skew={ZIPF_SKEW}, TTL={TTL_SECONDS/3600:.0f}h, "
          f"baseline=${BASELINE_PRICE_USD}/call, ours=${CACHE_PRICE_USD}/call\n")

    header = (
        f"{'req/day':>10} | {'hit rate':>9} | {'real fetches':>13} | "
        f"{'baseline $':>11} | {'our $':>9} | {'agent savings':>14} | {'savings %':>9}"
    )
    print(header)
    print("-" * len(header))

    for n in DAILY_VOLUMES:
        r = simulate(n)
        print(
            f"{r['requests_per_day']:>10,} | {r['cache_hit_rate']:>8.1%} | "
            f"{r['our_real_fetches']:>13,} | ${r['baseline_cost_usd']:>10,.2f} | "
            f"${r['our_cost_usd']:>8,.2f} | ${r['agent_savings_usd']:>13,.2f} | "
            f"{r['agent_savings_pct']:>8.1f}%"
        )

    print(
        "\nReading this: 'agent savings' is money agents keep by using this "
        "service instead of paying full price every time, at the SAME flat "
        "price we charge regardless of hit/miss. 'real fetches' is our own "
        "actual cost to serve - the gap between req/day and real fetches is "
        "what makes charging less than $0.01 sustainable rather than a "
        "loss-leader. Both numbers should grow *more* favorable as traffic "
        "grows (more overlap, more cache hits) - that's the flywheel."
    )


if __name__ == "__main__":
    main()
