import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.services.pipeline import build_pipeline_paths, run_full_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full source -> post_styles -> main/sub style pipeline.")
    parser.add_argument("--urls-file", default="data/source_urls.txt")
    parser.add_argument("--sources-dir", default="data/sources")
    parser.add_argument("--post-styles-dir", default="data/post_styles")
    parser.add_argument("--main-style-file", default="data/styles/main_style.json")
    parser.add_argument("--sub-style-file", default="data/styles/sub_style.json")
    parser.add_argument("--model", default="gpt-5")
    parser.add_argument("--skip-fetch", action="store_true")
    args = parser.parse_args()

    paths = build_pipeline_paths(
        project_root=PROJECT_ROOT,
        urls_file=args.urls_file,
        sources_dir=args.sources_dir,
        post_styles_dir=args.post_styles_dir,
        main_style_file=args.main_style_file,
        sub_style_file=args.sub_style_file,
    )
    run_full_pipeline(paths=paths, model=args.model, skip_fetch=args.skip_fetch)


if __name__ == "__main__":
    main()

