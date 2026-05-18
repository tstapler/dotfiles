// File: internal/user/repo.go (before move)
// This type will be moved to internal/repository/user.go
package user

// UserRepository provides access to user storage.
type UserRepository struct {
	store map[string]string
}

// NewUserRepository creates a new UserRepository.
func NewUserRepository() *UserRepository {
	return &UserRepository{store: make(map[string]string)}
}

// Save stores a user by ID.
func (r *UserRepository) Save(id, name string) {
	r.store[id] = name
}

// Find retrieves a user by ID.
func (r *UserRepository) Find(id string) (string, bool) {
	name, ok := r.store[id]
	return name, ok
}
