package main

import (
	"fmt"
	"net/http"
	"strings"
)

func handleSearch(w http.ResponseWriter, r *http.Request) {
	query := strings.TrimSpace(r.URL.Query().Get("q"))
	if query == "" {
		http.Error(w, "missing query", http.StatusBadRequest)
		return
	}
	fmt.Fprintf(w, "searching for: %s", query)
}

func main() {
	http.HandleFunc("/search", handleSearch)
}
