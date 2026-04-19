workspace(name = "stapler_scripts_repo")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# Rules Python for Python support in Bazel
http_archive(
    name = "rules_python",
    sha256 = "6f0b4070a25b774f2ec18683e336e4f3a73c17822986423c8a98d363717208d1",
    strip_prefix = "rules_python-0.31.0",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.31.0/rules_python-0.31.0.tar.gz",
)

load("@rules_python//python:repositories.bzl", "py_repositories")
py_repositories()
