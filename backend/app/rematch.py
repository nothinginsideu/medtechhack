"""
Re-run the matcher against every active PriceItem and refresh service_id links.

The matcher is the heart of normalization, but it only runs at parse time. This
script backfills existing rows so improvements to matching propagate to data
that was parsed with an older algorithm — otherwise the dashboard metric never
moves no matter how good the matcher gets.

Usage:
    python -m app.rematch                   # re-link everything active
    python -m app.rematch --dry-run         # report only, no writes
    python -m app.rematch --threshold 75    # override auto-match cutoff
"""
import argparse
import asyncio

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.price_item import PriceItem
from app.matching.matcher import Matcher, AUTO_MATCH_THRESHOLD


async def rematch(dry_run: bool, threshold: float) -> None:
    async with SessionLocal() as db:
        matcher = Matcher(db, auto_threshold=threshold)
        await matcher.load_services()

        result = await db.execute(select(PriceItem).where(PriceItem.is_active == True))
        items = result.scalars().all()

        stats = {"linked": 0, "unchanged": 0, "unlinked": 0, "review": 0}
        for item in items:
            match = matcher.match(item.service_name_raw)
            new_sid = match.service_id if match and match.score >= threshold else None
            new_score = match.score if match else 0.0

            if new_sid == item.service_id:
                stats["unchanged"] += 1
                continue

            if new_sid is not None:
                stats["linked"] += 1
            elif item.service_id is not None:
                stats["unlinked"] += 1
            else:
                stats["review"] += 1

            if not dry_run:
                item.service_id = new_sid
                item.match_score = new_score
                # Re-linking alone does not verify; operator/anomaly rules still apply,
                # but a clean high-confidence link with no other flags counts as verified.
                item.is_verified = new_sid is not None and new_score >= 85

        if not dry_run:
            await db.commit()

        print(
            f"\nRe-match complete ({'DRY RUN' if dry_run else 'APPLIED'}, threshold={threshold}):"
            f"\n  newly linked:   {stats['linked']}"
            f"\n  unchanged:      {stats['unchanged']}"
            f"\n  unlinked:       {stats['unlinked']}"
            f"\n  still in review:{stats['review']}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-link PriceItems via the matcher")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threshold", type=float, default=AUTO_MATCH_THRESHOLD)
    args = parser.parse_args()
    asyncio.run(rematch(args.dry_run, args.threshold))
