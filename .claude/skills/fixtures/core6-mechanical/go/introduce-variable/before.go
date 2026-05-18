package main

import (
	"fmt"
	"net/http"
	"strings"
)

func handleSearch(w http.ResponseWriter, r *http.Request) {
	if strings.TrimSpace(r.URL.Query().Get("q")) == "" {
		http.Error(w, "missing query", http.StatusBadRequest)
		return
	}
	fmt.Fprintf(w, "searching for: %s", strings.TrimSpace(r.URL.Query().Get("q")))
}

func main() {
	http.HandleFunc("/search", handleSearch)
}
