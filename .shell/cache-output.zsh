# Print-and-cache for slow `<tool> completion zsh` style generators: sets REPLY to a
# cache file keyed on the binary's mtime+size, so the tool only runs after an upgrade.
# zsh-only syntax, kept out of exports.sh so bash can still parse that file.
# Usage: _cache_output kubectl completion zsh && source "$REPLY"
_cache_output() {
    local exe=${commands[$1]} dir=${XDG_CACHE_HOME:-$HOME/.cache}/shell-eval name=${(j:_:)@}
    [[ -n $exe ]] || return 1
    local -A st
    zmodload -F zsh/stat b:zstat && zstat -H st -- $exe || return 1
    REPLY=$dir/$name.${st[mtime]}-${st[size]}
    [[ -s $REPLY ]] && return 0
    local -a stale
    mkdir -p $dir && "$@" >| $REPLY.$$ 2>/dev/null && [[ -s $REPLY.$$ ]] && mv -f $REPLY.$$ $REPLY || { rm -f $REPLY.$$; return 1; }
    stale=( $dir/$name.*(N) ); stale=( ${stale:#$REPLY} )
    (( $#stale )) && rm -f -- $stale
    return 0
}
