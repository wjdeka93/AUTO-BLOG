import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.services.style_extractor import extract_sub_style


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build sub_style JSON from post_styles using OpenAI Responses API.")
    parser.add_argument("--input-dir", default="data/post_styles")
    parser.add_argument("--main-style-file", default="data/styles/main_style.json")
    parser.add_argument("--output-file", default="data/styles/sub_style.json")
    parser.add_argument("--prompt-file", default="prompts/sub_style_extraction.txt")
    parser.add_argument("--schema-file", default="schemas/sub_style.schema.json")
    parser.add_argument("--model", default="gpt-5")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = extract_sub_style(
        model=args.model,
        prompt_file=Path(args.prompt_file),
        schema_file=Path(args.schema_file),
        input_dir=Path(args.input_dir),
        main_style_file=Path(args.main_style_file),
        output_file=Path(args.output_file),
    )
    print(f"Saved: {Path(args.output_file)}")
    print(f"Author: {result.get('author', '')}")


if __name__ == "__main__":
    main()

