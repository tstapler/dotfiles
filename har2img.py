#!/usr/bin/env python3
import json
import base64
import os
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Extract images from a HAR file and save them to a folder.")
    parser.add_argument("-i", "--input", type=str, required=True, help="Path to the HAR file.")
    parser.add_argument("-o", "--output", type=str, default="imgs", help="Directory where images will be saved. Default is 'imgs'.")
    return parser.parse_args()

def main():
    args = parse_args()

    # Make sure the output directory exists before running!
    folder = os.path.abspath(args.output)
    os.makedirs(folder, exist_ok=True)

    try:
        with open(args.input, "r") as f:
            har = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading HAR file: {e}")
        return

    entries = har.get("log", {}).get("entries", [])
    if not entries:
        print("No entries found in HAR file.")
        return

    for entry in entries:
        try:
            mimetype = entry["response"]["content"]["mimeType"]
            filename = entry["request"]["url"].split("/")[-1]
            image64 = entry["response"]["content"]["text"]
        except KeyError as e:
            print(f"KeyError: {e}")
            continue

        if mimetype not in ["image/webp", "image/jpeg", "image/png"]:
            print(f"Skipping unsupported MIME type: {mimetype}")
            continue

        ext = {
            "image/webp": "webp",
            "image/jpeg": "jpg",
            "image/png": "png",
        }.get(mimetype)

        file_path = os.path.join(folder, f"{filename}.{ext}")

        try:
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(image64))
            print(f"Successfully saved {file_path}")
        except Exception as e:
            print(f"Error writing file {file_path}: {e}")

if __name__ == "__main__":
    main()
