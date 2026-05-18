// File: src/core/user.ts (after move)
// Moved from src/services/user.ts — all import paths updated by ts-morph

export class UserService {
  private users: Map<string, string> = new Map();

  createUser(id: string, name: string): void {
    this.users.set(id, name);
  }

  getUser(id: string): string | undefined {
    return this.users.get(id);
  }

  listUsers(): string[] {
    return Array.from(this.users.values());
  }
}

export function createDefaultUserService(): UserService {
  return new UserService();
}
