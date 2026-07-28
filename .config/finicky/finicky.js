// @ts-check

/**
 * Finicky — https://github.com/johnste/finicky
 *
 * Finicky registers itself as the default browser, then dispatches each link
 * itself. Two reasons that is better than letting Chrome handle links directly:
 *
 *   1. Chrome opens external links in whichever profile is `profile.last_used`
 *      in its "Local State" file — i.e. whichever one you touched last. Nothing
 *      pins a link to a specific profile.
 *
 *   2. Automation (Playwright, WebDriver, MCP browser tools) launches
 *      /Applications/Google Chrome.app with its own --user-data-dir. Same bundle
 *      id, so LaunchServices can deliver the open-URL event to that throwaway
 *      instance instead of your real browser — links then land in a profile with
 *      none of your sign-ins. A leftover automation instance hijacks every link
 *      until it exits.
 *
 * Finicky sidesteps both because it launches the browser explicitly:
 *
 *   open -a "Google Chrome" -n --args --profile-directory=<dir> <url>
 *
 * `-n` is required: macOS drops --args when the target app is already running.
 * The new process then attaches to Chrome's process singleton, which is keyed on
 * the *default* user-data-dir, so it always reaches the real browser.
 *
 * `profile` is resolved against the profile's DISPLAY NAME first
 * (Local State -> profile.info_cache[*].name) and only then against the on-disk
 * directory name. The directory name is used below on purpose: display names on
 * this machine are misleading (the one labelled "Work" is an empty, signed-out
 * profile). List both with:
 *
 *   jq -r '.profile.info_cache | to_entries[] | [.key, .value.name, .value.user_name] | @tsv' \
 *     "$HOME/Library/Application Support/Google/Chrome/Local State"
 *
 * To route by the app that opened the link, add a handler:
 *
 *   handlers: [{ match: (url, { opener }) => opener?.name === "Slack",
 *                browser: { name: "Google Chrome", profile: "Profile 1" } }]
 *
 * @typedef {import('/Applications/Finicky.app/Contents/Resources/finicky.d.ts').FinickyConfig} FinickyConfig
 */

/** @type {FinickyConfig} */
export default {
  defaultBrowser: { name: "Google Chrome", profile: "Profile 1" },
  options: {
    // Homebrew owns the app version; don't self-update behind brew's back.
    checkForUpdates: false,
  },
};
