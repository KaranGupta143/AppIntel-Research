"""Command line entry point. Run `python -m src.main --help`."""
from __future__ import annotations
import argparse, logging
from . import analytics, config, researcher


def main() -> None:
    p = argparse.ArgumentParser(description="100-App Integration Research")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pilot", help="research the first 3 apps")
    r = sub.add_parser("research", help="research selected apps or all")
    r.add_argument("--ids", type=int, nargs="*", help="app ids, e.g. --ids 1 2 61")
    r.add_argument("--all", action="store_true", help="research all 100")
    r.add_argument("--force", action="store_true", help="redo apps already saved")
    s = sub.add_parser("review-sample", help="create a human review sheet")
    s.add_argument("--n", type=int, default=15); s.add_argument("--seed", type=int, default=42)
    s.add_argument("--pass-number", type=int, default=1)
    sub.add_parser("apply-reviews", help="apply human corrections to the dataset")
    sub.add_parser("build", help="export CSV, statistics and site/data.js")
    composio = sub.add_parser("composio-check", help="optional current-SDK and MCP credential check")
    composio.add_argument("--mcp", action="store_true", help="also create a hosted MCP endpoint")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.cmd == "pilot":
        try:
            researcher.run([1, 11, 61])
        except RuntimeError as exc:
            p.error(str(exc))
        researcher.export_results(researcher.load_results())
    elif args.cmd == "research":
        ids = [a.id for a in researcher.load_apps()] if args.all else (args.ids or [])
        if not ids:
            p.error("give --ids ... or --all")
        try:
            researcher.run(ids, force=args.force)
        except RuntimeError as exc:
            p.error(str(exc))
        researcher.export_results(researcher.load_results())
    elif args.cmd == "review-sample":
        sample = analytics.make_review_sample(list(researcher.load_results().values()), args.n, args.seed, args.pass_number)
        if sample.empty:
            print("No research results yet. Run the pilot first."); return
        if config.REVIEWS_FILE.exists():             # append, never overwrite human work
            existing = analytics.load_reviews()
            sample = analytics.pd.concat([existing, sample], ignore_index=True)
        sample = sample.drop_duplicates(
            subset=["app_id", "field", "pass_number"], keep="first"
        )
        sample.to_csv(config.REVIEWS_FILE, index=False)
        print(f"Wrote {config.REVIEWS_FILE}. Fill human_result, verdict, source_url, notes.")
    elif args.cmd == "apply-reviews":
        results = researcher.load_results()
        n = analytics.apply_corrections(results, analytics.load_reviews())
        researcher.save_results(results); print(f"Applied {n} human corrections.")
    elif args.cmd == "build":
        results = list(researcher.load_results().values())
        analytics.export_csv(results)
        payload = analytics.export_site_data(results, len(researcher.load_apps()))
        s = payload["stats"]
        print(f"Researched {s['researched']}/{s['total_apps']}. Dashboard data: {config.SITE_DATA_FILE}")
    elif args.cmd == "composio-check":
        from .composio_example import check_composio
        result = check_composio(config.COMPOSIO_API_KEY, args.mcp)
        print(f"Package installed: {'yes' if result.package_installed else 'no'}")
        print(f"API key configured: {'yes' if result.api_key_configured else 'no'}")
        print(f"Session created: {'yes' if result.session_created else 'no'}")
        if args.mcp:
            print(f"Hosted MCP endpoint created: {'yes' if result.mcp_endpoint_created else 'no'}")
        print(result.detail)


if __name__ == "__main__":
    main()
