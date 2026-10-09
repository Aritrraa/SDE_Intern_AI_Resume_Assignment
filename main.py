"""
CLI entry point for the AI Resume Screening & Ranking System.

Usage:
    python main.py --input ./resumes --output ./output/results.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="AI Resume Screening & Ranking System",
        epilog="Example: python main.py --input ./resumes --output ./output/results.json",
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to directory containing resume files (PDF, optionally DOCX/TXT)",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path for the output JSON results file",
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="Disable GitHub enrichment (useful for offline runs or testing)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM project assessment (fallback to deterministic mode)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    # Validate input directory
    input_dir = args.input
    if not os.path.isdir(input_dir):
        logger.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run pipeline
    from src.pipeline import run_pipeline

    logger.info("=" * 60)
    logger.info("AI Resume Screening & Ranking System")
    logger.info("=" * 60)
    logger.info("Input directory: %s", input_dir)
    logger.info("Output file: %s", args.output)
    logger.info("GitHub enrichment: %s", "disabled" if args.no_github else "enabled")
    logger.info("LLM assessment: %s", "disabled" if args.no_llm else "enabled")
    logger.info("=" * 60)

    try:
        results = run_pipeline(
            input_dir=input_dir,
            enable_github=not args.no_github,
            enable_llm=not args.no_llm,
        )
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        sys.exit(1)

    # Write output
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info("Results written to %s", output_path)
    except Exception as e:
        logger.error("Failed to write output: %s", e)
        sys.exit(1)

    # Print summary to console
    summary = results["batch_summary"]
    print("\n" + "=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)
    print(f"  Total resumes processed:  {summary['total_resumes']}")
    print(f"  Successfully parsed:      {summary['successfully_parsed']}")
    print(f"  Eligible candidates:      {summary['eligible']}")
    print(f"  Rejected candidates:      {summary['rejected']}")
    print(f"  Failed/unreadable:        {summary['failed_unreadable']}")
    print("=" * 60)

    # Print top candidates
    ranked = results["ranked_candidates"]
    if ranked:
        print("\nTOP CANDIDATES:")
        print("-" * 60)
        for c in ranked[:10]:
            print(f"  #{c['rank']:2d} | {c['total_score']:3d} pts | {c['candidate_name']}")
            bd = c["score_breakdown"]
            print(f"       AI:{bd['ai_project_depth']:2d} Py:{bd['python_backend']:2d} "
                  f"Cloud:{bd['cloud_fullstack']:2d} GH:{bd['github']:2d} Eng:{bd['engineering_depth']:1d}")
        if len(ranked) > 10:
            print(f"  ... and {len(ranked) - 10} more eligible candidates")
        print("-" * 60)

    # Print rejected candidates
    rejected = results["rejected_candidates"]
    if rejected:
        print(f"\nREJECTED CANDIDATES ({len(rejected)}):")
        print("-" * 60)
        for c in rejected:
            reasons = "; ".join(c["rejection_reasons"])
            print(f"  {c['candidate_name']} — {reasons}")
        print("-" * 60)

    # Print failed files
    failed = results["failed_files"]
    if failed:
        print(f"\nFAILED FILES ({len(failed)}):")
        for f in failed:
            print(f"  {f['filename']}: {f['error']}")

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
