import os
import json
import base64
import pytest
import sys
from har2img import process_har

def test_process_har_success(tmp_path):
    output_dir = tmp_path / "imgs"
    output_dir.mkdir()

    # Mock data: a simple transparent 1x1 PNG image
    # iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==
    image_content = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    har_data = {
        "log": {
            "entries": [
                {
                    "request": {"url": "http://example.com/test.png"},
                    "response": {
                        "content": {
                            "mimeType": "image/png",
                            "text": image_content
                        }
                    }
                }
            ]
        }
    }

    process_har(har_data, str(output_dir))

    output_file = output_dir / "test.png.png"
    assert output_file.exists()
    with open(output_file, "rb") as f:
        assert f.read() == base64.b64decode(image_content)

def test_process_har_key_error(tmp_path, capsys):
    output_dir = tmp_path / "imgs"
    output_dir.mkdir()

    har_data = {
        "log": {
            "entries": [
                {
                    # Missing 'request' key
                    "response": {
                        "content": {
                            "mimeType": "image/png",
                            "text": "somebase64"
                        }
                    }
                },
                {
                    # Missing 'mimeType'
                    "request": {"url": "http://example.com/test2.png"},
                    "response": {
                        "content": {
                            "text": "somebase64"
                        }
                    }
                }
            ]
        }
    }

    process_har(har_data, str(output_dir))

    captured = capsys.readouterr()
    assert "KeyError: 'request'" in captured.out
    assert "KeyError: 'mimeType'" in captured.out
    assert len(list(output_dir.iterdir())) == 0

def test_process_har_unsupported_mimetype(tmp_path, capsys):
    output_dir = tmp_path / "imgs"
    output_dir.mkdir()

    har_data = {
        "log": {
            "entries": [
                {
                    "request": {"url": "http://example.com/test.txt"},
                    "response": {
                        "content": {
                            "mimeType": "text/plain",
                            "text": "not an image"
                        }
                    }
                }
            ]
        }
    }

    process_har(har_data, str(output_dir))

    captured = capsys.readouterr()
    assert "Skipping unsupported MIME type: text/plain" in captured.out
    assert len(list(output_dir.iterdir())) == 0

def test_process_har_no_entries(capsys):
    har_data = {"log": {"entries": []}}
    process_har(har_data, "some_dir")

    captured = capsys.readouterr()
    assert "No entries found in HAR file." in captured.out

def test_process_har_mixed_entries(tmp_path, capsys):
    output_dir = tmp_path / "imgs"
    output_dir.mkdir()

    image_content = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    har_data = {
        "log": {
            "entries": [
                {
                    "request": {"url": "http://example.com/invalid.png"},
                    "response": {
                        "content": {
                            # Missing 'text' key
                            "mimeType": "image/png"
                        }
                    }
                },
                {
                    "request": {"url": "http://example.com/valid.png"},
                    "response": {
                        "content": {
                            "mimeType": "image/png",
                            "text": image_content
                        }
                    }
                }
            ]
        }
    }

    process_har(har_data, str(output_dir))

    captured = capsys.readouterr()
    assert "KeyError: 'text'" in captured.out
    assert "Successfully saved" in captured.out

    assert (output_dir / "valid.png.png").exists()
    assert not (output_dir / "invalid.png.png").exists()

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
