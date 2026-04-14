import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.services.source_fetcher import fetch_all_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Naver blog posts and save source text files.")
    parser.add_argument("--urls-file", default="data/source_urls.txt")
    parser.add_argument("--output-dir", default="data/sources")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    for source_post in fetch_all_sources(Path(args.urls_file), output_dir):
        source_path = output_dir / f"{source_post.metadata['post_id']}.txt"
        print(f"saved source: {source_path}")
        print(f"  title={source_post.metadata['title']}")
        print(f"  published_at={source_post.metadata['published_at']}")
        print(f"  author={source_post.metadata['author']}")
        print(f"  category={source_post.metadata['category']}")


if __name__ == "__main__":
    main()

