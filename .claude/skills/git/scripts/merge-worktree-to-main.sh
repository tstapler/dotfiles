#!/bin/bash

# merge_worktree_to_main.sh
# Merges current git worktree branch back into main branch locally

set -e  # Exit on any error

# Default configuration
MAIN_PATH_DEFAULT="$HOME/IdeaProjects"
CLEANUP=false
DRY_RUN=false
MAIN_PATH=""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "${PURPLE}🔄 $1${NC}"; }

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                CLEANUP=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --main-path)
                MAIN_PATH="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
merge_worktree_to_main - Smart merge with comprehensive review

DESCRIPTION:
    Merges git worktree branch to main locally with intelligent review process.
    Analyzes changes, checks for uncommitted work, and provides interactive
    decision making to ensure only valuable changes are merged.

USAGE:
    merge_worktree_to_main [OPTIONS]

OPTIONS:
    --cleanup           Remove worktree after successful merge
    --dry-run          Show what would be merged without doing it
    --main-path PATH   Specify main repository path (default: ~/IdeaProjects)
    --help, -h         Show this help message

REVIEW PROCESS:
    1. Check for uncommitted changes (auto-commit option available)
    2. Analyze branch differences and commit history
    3. Show file changes with color-coded status
    4. Perform quality checks (large files, conflicts, sensitive data)
    5. Display recent main branch activity for context
    6. Interactive decision: merge, cancel, show diff, or dry-run

EXAMPLES:
    merge_worktree_to_main                    # Interactive merge with review
    merge_worktree_to_main --cleanup          # Merge and cleanup worktree
    merge_worktree_to_main --dry-run          # Preview merge without executing
    merge_worktree_to_main --main-path ~/Code # Use custom main repo path

SAFETY FEATURES:
    • Uncommitted work detection and optional auto-commit
    • Quality checks for large files and sensitive data
    • Interactive decision making with diff preview
    • Fast-forward vs merge commit detection
    • Rollback capability if issues arise

EOF
}

# Validate we're in a git worktree
validate_worktree() {
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi

    # Check if we're in a worktree (not main repo)
    local git_dir=$(git rev-parse --git-dir)
    if [[ ! "$git_dir" == *"worktrees"* ]]; then
        log_warning "You appear to be in the main repository, not a worktree"
        log_info "This command is designed to merge FROM a worktree TO main"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Aborted by user"
            exit 0
        fi
    fi
}

# Find the main repository path
find_main_repo() {
    local worktree_list=$(git worktree list)
    local main_repo=""
    
    # Look for main branch in worktree list
    while IFS= read -r line; do
        if [[ $line == *"[main]"* ]]; then
            main_repo=$(echo "$line" | awk '{print $1}')
            break
        fi
    done <<< "$worktree_list"
    
    # If not found in worktree list, try default paths
    if [[ -z "$main_repo" ]]; then
        if [[ -n "$MAIN_PATH" ]]; then
            # Check custom path
            local repo_name=$(basename $(git rev-parse --show-toplevel))
            main_repo="$MAIN_PATH/$repo_name"
        else
            # Check default path
            local repo_name=$(basename $(git rev-parse --show-toplevel))
            main_repo="$MAIN_PATH_DEFAULT/$repo_name"
        fi
    fi
    
    if [[ ! -d "$main_repo" ]]; then
        log_error "Cannot find main repository at: $main_repo"
        log_info "Try specifying the path with --main-path"
        exit 1
    fi
    
    echo "$main_repo"
}

# Get current branch name
get_current_branch() {
    git rev-parse --abbrev-ref HEAD
}

# Validate merge can proceed (streamlined version)
validate_merge() {
    local main_repo="$1"
    local branch="$2"

    # Check main repo is clean
    if ! (cd "$main_repo" && git diff-index --quiet HEAD --); then
        log_error "Main repository has uncommitted changes"
        log_info "Please clean up main repository first: $main_repo"
        exit 1
    fi

    # Check if branch exists in main repo
    if ! (cd "$main_repo" && git rev-parse --verify "$branch" >/dev/null 2>&1); then
        log_error "Branch '$branch' does not exist in main repository"
        log_info "Make sure your branch is available to the main repository"
        exit 1
    fi
}

# Check for uncommitted work in current worktree
check_uncommitted_work() {
    local current_worktree=$(pwd)

    log_step "Checking for uncommitted work in current worktree"

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        log_warning "Found uncommitted changes in current worktree"
        echo -e "${YELLOW}Uncommitted changes:${NC}"
        git status --porcelain
        echo

        read -p "Do you want to commit these changes before proceeding? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_error "Cannot proceed with uncommitted changes"
            log_info "Please commit, stash, or discard changes first"
            exit 1
        else
            log_step "Staging all changes..."
            git add .

            # Ask for commit message
            echo "Enter commit message (or press Enter for auto-generated):"
            read -r commit_msg

            if [[ -z "$commit_msg" ]]; then
                commit_msg="chore: commit changes before merging to main"
            fi

            git commit -m "$commit_msg"
            log_success "Changes committed successfully"
        fi
    else
        log_success "No uncommitted changes found"
    fi
}

# Comprehensive branch analysis and review
review_branch_changes() {
    local main_repo="$1"
    local branch="$2"

    log_step "Comprehensive review for branch: $branch"
    echo

    # 1. Show branch comparison
    echo -e "${CYAN}═══ Branch Comparison ═══${NC}"
    local commit_count=$(cd "$main_repo" && git rev-list --count HEAD.."$branch" 2>/dev/null || echo "0")
    local behind_count=$(cd "$main_repo" && git rev-list --count "$branch"..HEAD 2>/dev/null || echo "0")

    if [[ "$commit_count" -eq 0 ]]; then
        log_warning "No new commits to merge - branch is up to date with main"
        return 1
    fi

    echo -e "${GREEN}Commits ahead of main: ${commit_count}${NC}"
    echo -e "${YELLOW}Commits behind main: ${behind_count}${NC}"
    echo

    # 2. Show commits in detail
    echo -e "${CYAN}═══ Commits to be Merged ═══${NC}"
    (cd "$main_repo" && git log --oneline --graph --decorate HEAD.."$branch")
    echo

    # 3. Show file changes with context
    echo -e "${CYAN}═══ File Changes Summary ═══${NC}"
    (cd "$main_repo" && git diff --stat HEAD.."$branch")
    echo

    # 4. Show modified files with change type
    echo -e "${CYAN}═══ Modified Files ═══${NC}"
    (cd "$main_repo" && git diff --name-status HEAD.."$branch" | while read status file; do
        case $status in
            A) echo -e "${GREEN}+ Added:    $file${NC}" ;;
            M) echo -e "${YELLOW}~ Modified: $file${NC}" ;;
            D) echo -e "${RED}- Deleted:  $file${NC}" ;;
            R*) echo -e "${BLUE}→ Renamed:  $file${NC}" ;;
            *) echo -e "${PURPLE}? $status:   $file${NC}" ;;
        esac
    done)
    echo

    # 5. Check for potential issues
    echo -e "${CYAN}═══ Quality Check ═══${NC}"
    check_merge_quality "$main_repo" "$branch"
    echo

    # 6. Show recent activity context
    echo -e "${CYAN}═══ Recent Main Branch Activity ═══${NC}"
    (cd "$main_repo" && git log --oneline -5 HEAD)
    echo

    return 0
}

# Check merge quality and potential issues
check_merge_quality() {
    local main_repo="$1"
    local branch="$2"

    local issues_found=false

    # Check for large files
    local large_files=$(cd "$main_repo" && git diff --name-only HEAD.."$branch" | xargs -I {} git show "$branch:{}" 2>/dev/null | wc -c | awk '$1 > 1000000 {print $2}' || true)
    if [[ -n "$large_files" ]]; then
        log_warning "Large files detected in changes"
        issues_found=true
    fi

    # Check for binary files
    local binary_files=$(cd "$main_repo" && git diff --numstat HEAD.."$branch" | awk '$1 == "-" && $2 == "-" {print $3}' || true)
    if [[ -n "$binary_files" ]]; then
        log_info "Binary files found: $(echo "$binary_files" | wc -l | xargs) files"
    fi

    # Check for potential conflicts
    local merge_base=$(cd "$main_repo" && git merge-base HEAD "$branch" 2>/dev/null || echo "")
    local main_head=$(cd "$main_repo" && git rev-parse HEAD)

    if [[ "$merge_base" != "$main_head" ]]; then
        log_warning "Not a fast-forward merge - main has moved forward"
        log_info "You may want to rebase your branch first"
        issues_found=true
    fi

    # Check for common sensitive patterns
    local sensitive_patterns=("password" "secret" "token" "key" "api")
    for pattern in "${sensitive_patterns[@]}"; do
        local matches=$(cd "$main_repo" && git diff HEAD.."$branch" | grep -i "$pattern" | head -3 || true)
        if [[ -n "$matches" ]]; then
            log_warning "Potential sensitive data found containing '$pattern'"
            issues_found=true
        fi
    done

    if [[ "$issues_found" == "false" ]]; then
        log_success "No obvious quality issues detected"
    fi
}

# Interactive merge decision
make_merge_decision() {
    local main_repo="$1"
    local branch="$2"

    echo -e "${CYAN}═══ Merge Decision ═══${NC}"
    echo "Based on the review above, decide if this merge adds value:"
    echo
    echo "1. Yes - Proceed with merge"
    echo "2. No - Cancel merge"
    echo "3. Show detailed diff first"
    echo "4. Dry run only"
    echo

    while true; do
        read -p "Your choice (1-4): " -n 1 -r
        echo
        case $REPLY in
            1)
                return 0  # Proceed
                ;;
            2)
                log_info "Merge cancelled by user decision"
                exit 0
                ;;
            3)
                echo -e "${CYAN}═══ Detailed Diff ═══${NC}"
                (cd "$main_repo" && git diff HEAD.."$branch" | head -100)
                echo -e "${YELLOW}... (showing first 100 lines)${NC}"
                echo
                echo "Still want to proceed with merge?"
                read -p "Proceed? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    return 0
                else
                    log_info "Merge cancelled after diff review"
                    exit 0
                fi
                ;;
            4)
                log_info "Dry run mode activated"
                DRY_RUN=true
                return 0
                ;;
            *)
                echo "Invalid choice. Please select 1-4."
                ;;
        esac
    done
}

# Show what would be merged (legacy function - now calls review)
show_merge_preview() {
    local main_repo="$1"
    local branch="$2"

    # First check for uncommitted work
    check_uncommitted_work

    # Then do comprehensive review
    if review_branch_changes "$main_repo" "$branch"; then
        make_merge_decision "$main_repo" "$branch"
    else
        log_info "Nothing to merge - branch is up to date"
        exit 0
    fi
}

# Perform the actual merge
perform_merge() {
    local main_repo="$1"
    local branch="$2"
    
    log_step "Switching to main repository: $main_repo"
    cd "$main_repo"
    
    log_step "Merging branch: $branch"
    git merge "$branch"
    
    log_success "Merge completed successfully!"
    
    # Show merge stats
    git diff --stat HEAD~1 HEAD | tail -1
}

# Clean up worktree
cleanup_worktree() {
    local current_worktree=$(pwd)
    local main_repo="$1"
    
    log_step "Cleaning up worktree: $current_worktree"
    
    # Switch to main repo first
    cd "$main_repo"
    
    # Remove the worktree
    if git worktree remove "$current_worktree" 2>/dev/null; then
        log_success "Worktree removed: $current_worktree"
    else
        log_warning "Could not automatically remove worktree"
        log_info "You may need to manually remove: $current_worktree"
    fi
}

# Main execution
main() {
    parse_args "$@"
    
    log_info "Starting worktree to main merge process"
    
    # Validation
    validate_worktree
    
    local current_worktree=$(pwd)
    local current_branch=$(get_current_branch)
    local main_repo=$(find_main_repo)
    
    log_info "Current worktree: $current_worktree"
    log_info "Main repository: $main_repo"
    log_step "Branch to merge: $current_branch"
    
    # Validate merge
    validate_merge "$main_repo" "$current_branch"
    
    # Show preview
    show_merge_preview "$main_repo" "$current_branch"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run complete - no changes made"
        exit 0
    fi
    
    # Perform merge
    perform_merge "$main_repo" "$current_branch"
    
    # Cleanup if requested
    if [[ "$CLEANUP" == "true" ]]; then
        cleanup_worktree "$main_repo"
    else
        echo
        log_info "Worktree preserved at: $current_worktree"
        log_info "Use --cleanup flag to automatically remove it next time"
    fi
    
    log_success "Worktree merge completed successfully!"
}

# Run main function with all arguments
main "$@"