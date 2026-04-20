#!/usr/bin/env bash
#
# discover-api.sh - Quick Java API discovery helper
#
# Usage:
#   ./discover-api.sh find <library-name>     # Find JAR location
#   ./discover-api.sh list <jar> <package>    # List classes in package
#   ./discover-api.sh api <jar> <class>       # Show public API
#   ./discover-api.sh getters <jar> <class>   # Show getters only
#   ./discover-api.sh full <jar> <class>      # Full signatures with generics

set -euo pipefail

usage() {
    cat <<EOF
Java API Discovery Helper

Usage:
    $(basename "$0") find <library-name>        Find JAR in Gradle/Maven caches
    $(basename "$0") list <jar> <package>       List classes in package
    $(basename "$0") api <jar> <class>          Show public API methods
    $(basename "$0") getters <jar> <class>      Show getter methods only
    $(basename "$0") setters <jar> <class>      Show setter/builder methods
    $(basename "$0") full <jar> <class>         Full signatures with generics
    $(basename "$0") search <jar> <class> <term> Search for specific method

Examples:
    $(basename "$0") find datadog-api-client
    $(basename "$0") api ~/.gradle/.../lib.jar com.example.MyClass
    $(basename "$0") getters lib.jar com.example.Model
    $(basename "$0") search lib.jar com.example.Api page
EOF
    exit 1
}

cmd_find() {
    local name="$1"
    echo "=== Gradle Cache ==="
    find ~/.gradle/caches -name "*${name}*.jar" -type f 2>/dev/null | head -10 || echo "None found"
    echo ""
    echo "=== Maven Repository ==="
    find ~/.m2/repository -name "*${name}*.jar" -type f 2>/dev/null | head -10 || echo "None found"
}

cmd_list() {
    local jar="$1"
    local package="$2"
    jar tf "$jar" | grep "${package//.//}" | grep '\.class$' | sed 's/\.class$//' | sed 's/\//./g' | head -30
}

cmd_api() {
    local jar="$1"
    local class="$2"
    javap -cp "$jar" "$class"
}

cmd_getters() {
    local jar="$1"
    local class="$2"
    javap -cp "$jar" "$class" | grep -E "public.*get[A-Z]"
}

cmd_setters() {
    local jar="$1"
    local class="$2"
    javap -cp "$jar" "$class" | grep -E "public.*(set[A-Z]|with[A-Z]|build)"
}

cmd_full() {
    local jar="$1"
    local class="$2"
    javap -s -cp "$jar" "$class"
}

cmd_search() {
    local jar="$1"
    local class="$2"
    local term="$3"
    javap -cp "$jar" "$class" | grep -i "$term"
}

# Main
[[ $# -lt 1 ]] && usage

command="$1"
shift

case "$command" in
    find)
        [[ $# -lt 1 ]] && usage
        cmd_find "$1"
        ;;
    list)
        [[ $# -lt 2 ]] && usage
        cmd_list "$1" "$2"
        ;;
    api)
        [[ $# -lt 2 ]] && usage
        cmd_api "$1" "$2"
        ;;
    getters)
        [[ $# -lt 2 ]] && usage
        cmd_getters "$1" "$2"
        ;;
    setters)
        [[ $# -lt 2 ]] && usage
        cmd_setters "$1" "$2"
        ;;
    full)
        [[ $# -lt 2 ]] && usage
        cmd_full "$1" "$2"
        ;;
    search)
        [[ $# -lt 3 ]] && usage
        cmd_search "$1" "$2" "$3"
        ;;
    *)
        usage
        ;;
esac
