setup_rust() {
  rustup update
  rustup default stable
  rustup component add rls-preview rust-analysis rust-src
}
