import argparse
import json
import base64
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EmojiDTO:
    name: str
    content: bytes


def extract_emoji_data_from_har(har_filepath: Path) -> list[EmojiDTO]:
    """Extracts Slack emoji data from a given HAR file."""
    with open(har_filepath, 'r') as f:
        har_data = json.load(f)

    emojis = []

    for entry in har_data.get('log', {}).get('entries', []):
        url = entry.get('request', {}).get('url', "")
        if "emoji.slack-edge.com" in url:
            # Extract the name of the emoji from the URL.
            emoji_name = url.split('/')[-2]

            # Decode the base64 content of the response.
            content_encoding = entry.get('response', {}).get('content', {}).get('encoding')
            content_text = entry.get('response', {}).get('content', {}).get('text', "")

            if content_encoding == "base64":
                content_bytes = base64.b64decode(content_text)
                emojis.append(EmojiDTO(name=emoji_name, content=content_bytes))

    return emojis


def save_emoji(emoji: EmojiDTO, output_directory: Path) -> None:
    """Saves an emoji to the given directory."""
    output_directory.mkdir(parents=True, exist_ok=True)
    with open(output_directory / f"{emoji.name}.png", "wb") as f:
        f.write(emoji.content)


def main(args):
    print("Extracting emoji data...")
    emojis = extract_emoji_data_from_har(args.har_filepath)

    if not emojis:
        print("No emojis found.")
        return

    args.output_directory.mkdir(parents=True, exist_ok=True)

    for emoji in emojis:
        print(f"Saving {emoji.name}...")
        save_emoji(emoji, args.output_directory)

    print("All emojis saved successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extracts Slack emojis from a HAR file.')
    parser.add_argument('har_filepath', type=Path, help='Path to the HAR file')
    parser.add_argument('output_directory', type=Path, help='Directory to save extracted emojis')

    args = parser.parse_args()
    main(args)
