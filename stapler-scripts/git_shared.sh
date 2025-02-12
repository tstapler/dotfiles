#!/usr/bin/env sh

# vim: ai ts=2 sw=2 et sts=2 ft=sh

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
            echo "tystapler@gmail.com"
            ;;
    esac
}
