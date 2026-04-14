import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.services.naver_blog import normalize_naver_blog_url
from core.services.style_extractor import extract_post_style_from_file, extract_post_style_from_url


def resolve_output_file(args: argparse.Namespace, post_id: str) -> Path:
    if args.output_file:
        return Path(args.output_file)
    return Path("data/post_styles") / f"{post_id}.json"


def resolve_source_file(args: argparse.Namespace, post_id: str) -> Path:
    if args.source_output_file:
        return Path(args.source_output_file)
    return Path("data/sources") / f"{post_id}.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract a Naver blog post into post_style JSON using OpenAI Responses API.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-file", help="UTF-8 text file containing the blog post body.")
    input_group.add_argument("--url", help="Naver blog post URL. The script will fetch and extract the post body.")

    parser.add_argument("--output-file", help="Where to save the extracted post_style JSON.")
    parser.add_argument("--source-output-file", help="Where to save the fetched source text when using --url.")

    parser.add_argument("--post-id")
    parser.add_argument("--title")
    parser.add_argument("--published-at", default=None)
    parser.add_argument("--author", default="")
    parser.add_argument("--category", default="")

    parser.add_argument("--model", default="gpt-5")
    parser.add_argument("--prompt-file", default="prompts/post_style_extraction.txt")
    parser.add_argument("--schema-file", default="schemas/post_style.schema.json")
    return parser.parse_args()


def build_metadata_from_args(args: argparse.Namespace) -> dict[str, str | None]:
    required = {
        "post_id": args.post_id,
        "url": args.url,
        "title": args.title,
        "author": args.author,
        "category": args.category,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"--input-file 사용 시 다음 인자가 필요합니다: {', '.join(missing)}")

    return {
        "post_id": args.post_id,
        "url": args.url,
        "title": args.title,
        "published_at": args.published_at,
        "author": args.author,
        "category": args.category,
    }


def main() -> None:
    args = parse_args()

    if args.url and not args.input_file:
        _, post_id = normalize_naver_blog_url(args.url)
        output_path = resolve_output_file(args, post_id)
        source_output_path = resolve_source_file(args, post_id)
        result = extract_post_style_from_url(
            url=args.url,
            model=args.model,
            prompt_file=Path(args.prompt_file),
            schema_file=Path(args.schema_file),
            output_file=output_path,
            source_output_file=source_output_path,
        )
        print(f"Saved post_style: {output_path}")
        print(f"Saved source text: {source_output_path}")
    else:
        metadata = build_metadata_from_args(args)
        output_path = resolve_output_file(args, metadata["post_id"] or "")
        result = extract_post_style_from_file(
            model=args.model,
            prompt_file=Path(args.prompt_file),
            schema_file=Path(args.schema_file),
            input_file=Path(args.input_file),
            output_file=output_path,
            metadata=metadata,
        )
        print(f"Saved post_style: {output_path}")

    print(f"Post id: {result.get('post_id', '')}")


if __name__ == "__main__":
    main()

