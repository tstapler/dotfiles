# Slack Emoji Extraction

This script is meant to help you extract all the custom emoji from your Slack workspace. 


## Downloading HAR files with Emojis

1. Open Slack in your browser for your organization
2. Open the developer tools
3. Navigate to the network tab
4. Open the emoji picker in slack, click the "Custom Emojis" selector and scroll down to the bottom of the list
5. Click on the down arrow at the top of the network tab to download the HAR file.

## Running the script

```shell
python extract_slack_emoji.py ~/Downoads/app.slack.com.har ~/Pictures/my-slack-emoji
```