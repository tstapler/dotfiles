#!/usr/bin/env sh

# vim: ai ts=2 sw=2 et sts=2 ft=sh

# Maps a git remote URL to the email that should author commits there.
#
# Prints the email on a match and NOTHING when no rule matches. Empty output
# means "no opinion" — it is deliberately not a default. Callers must treat it
# as "leave the configured identity alone" rather than substituting a guess:
# silently rewriting user.email to the personal address in every unrecognized
# repo is how work commits end up authored personally, and it also clobbers a
# deliberate `git config user.email`. Machine-local overlays can add their own
# org rules via the ~/.config/git-hooks/pre-commit.d/ drop-in loop in
# .gittemplates/hooks/pre-commit, which runs after set_git_emails.
get_git_email() {
    ORIGIN_URL="$1"
    case $ORIGIN_URL in
        *github.com/fanatics*|*github.com:fanatics*)
            echo "tyler.stapler@betfanatics.com"
            ;;
        *github.com/Workiva*|*github.com:Workiva*|\
        *github.com/workiva*|*github.com:workiva*|\
        *github.com/*-wf*|*github.com:*-wf*|\
        *github.com/*-wk*|*github.com:*-wk*)
            echo "tyler.stapler@workiva.com"
            ;;
        *.googlesource.com*|sso://*)
            echo "tstapler@google.com"
            ;;
        *github.com/tstapler*|*github.com:tstapler*)
            echo "tystapler@gmail.com"
            ;;
        *)
            # No opinion. See the note above: do NOT default to the personal
            # address here — an unrecognized host is not evidence that a repo is
            # personal.
            ;;
    esac
}

# The address to fall back to only when a repo has NO email configured at all
# and no rule matched, so that a commit can still be made rather than failing on
# an unset identity.
get_git_email_default() {
    echo "tystapler@gmail.com"
}
