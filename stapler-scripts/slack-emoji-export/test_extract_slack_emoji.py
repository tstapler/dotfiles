import json
import base64
from pathlib import Path
import pytest
from extract_slack_emoji import extract_emoji_data_from_har, save_emoji, EmojiDTO

def test_extract_emoji_data_from_har_happy_path(tmp_path):
    har_content = {
        "log": {
            "entries": [
                {
                    "request": {"url": "https://emoji.slack-edge.com/T123/emoji1/emoji1.png"},
                    "response": {
                        "content": {
                            "encoding": "base64",
                            "text": base64.b64encode(b"fake-image-content-1").decode("utf-8")
                        }
                    }
                },
                {
                    "request": {"url": "https://emoji.slack-edge.com/T123/emoji2/emoji2.png"},
                    "response": {
                        "content": {
                            "encoding": "base64",
                            "text": base64.b64encode(b"fake-image-content-2").decode("utf-8")
                        }
                    }
                }
            ]
        }
    }
    har_file = tmp_path / "test.har"
    har_file.write_text(json.dumps(har_content))

    emojis = extract_emoji_data_from_har(har_file)

    assert len(emojis) == 2
    assert emojis[0].name == "emoji1"
    assert emojis[0].content == b"fake-image-content-1"
    assert emojis[1].name == "emoji2"
    assert emojis[1].content == b"fake-image-content-2"

def test_extract_emoji_data_from_har_no_emojis(tmp_path):
    har_content = {
        "log": {
            "entries": [
                {
                    "request": {"url": "https://other.com/image.png"},
                    "response": {"content": {"encoding": "base64", "text": "YWJj"}}
                }
            ]
        }
    }
    har_file = tmp_path / "test.har"
    har_file.write_text(json.dumps(har_content))

    emojis = extract_emoji_data_from_har(har_file)
    assert len(emojis) == 0

def test_extract_emoji_data_from_har_missing_fields(tmp_path):
    har_content = {
        "log": {
            "entries": [
                {
                    "request": {"url": "https://emoji.slack-edge.com/T123/emoji1/emoji1.png"},
                    "response": {
                        "content": {
                            # missing encoding and text
                        }
                    }
                }
            ]
        }
    }
    har_file = tmp_path / "test.har"
    har_file.write_text(json.dumps(har_content))

    emojis = extract_emoji_data_from_har(har_file)
    # The code uses .get() with defaults, so it should handle missing fields gracefully but return no emoji if encoding/text are missing.
    assert len(emojis) == 0

def test_extract_emoji_data_from_har_non_base64(tmp_path):
    har_content = {
        "log": {
            "entries": [
                {
                    "request": {"url": "https://emoji.slack-edge.com/T123/emoji1/emoji1.png"},
                    "response": {
                        "content": {
                            "encoding": "gzip",
                            "text": "some-text"
                        }
                    }
                }
            ]
        }
    }
    har_file = tmp_path / "test.har"
    har_file.write_text(json.dumps(har_content))

    emojis = extract_emoji_data_from_har(har_file)
    assert len(emojis) == 0

def test_extract_emoji_data_from_har_empty_log(tmp_path):
    har_file = tmp_path / "test.har"
    har_file.write_text(json.dumps({}))

    emojis = extract_emoji_data_from_har(har_file)
    assert len(emojis) == 0

def test_save_emoji(tmp_path):
    emoji = EmojiDTO(name="test_emoji", content=b"fake-content")
    output_dir = tmp_path / "output"

    save_emoji(emoji, output_dir)

    expected_file = output_dir / "test_emoji.png"
    assert expected_file.exists()
    assert expected_file.read_bytes() == b"fake-content"
