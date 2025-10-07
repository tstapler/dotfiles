---
title: Does It Work
description: Review if changes are ready for commit and review
arguments: []
---

# Does It Work Review

This command helps evaluate if the current branch changes are ready for commit and review. I'll perform a comprehensive readiness check on your code changes, focusing on:

1. Code compilation/build status
2. Test suite results
3. Code quality checks
4. Manual testing verification

## Analysis Process

I'll run through the following steps:

1. **Check git status and changes**
   - Review what files have been modified
   - Analyze the scope and impact of changes

2. **Verify build/compilation**
   - Run appropriate build commands based on the project type
   - For Java: `./gradlew clean build`
   - Report any compilation errors or warnings

3. **Check test suite**
   - Run unit tests and integration tests
   - For Java: `./gradlew test` and `./gradlew testIntegration`
   - Report on test coverage and any failing tests

4. **Code quality verification**
   - Run linting and formatting checks
   - For Java: `./gradlew checkstyleMain` and `./gradlew spotlessCheck`
   - Identify any style violations or potential issues

5. **Manual testing verification**
   - Prompt you about manual testing scenarios
   - Confirm if you've tested all user-facing changes
   - Document test scenarios that have been covered

## Report

I'll provide a comprehensive report with:
- ✅ Items that pass verification
- ❌ Items that need attention
- 🔍 Suggestions for additional testing or verification
- 📝 A readiness summary

## Recommendations

Based on the verification results, I'll recommend whether the code is:
- Ready for commit and PR
- Needs specific fixes before proceeding
- Requires additional tests or validation