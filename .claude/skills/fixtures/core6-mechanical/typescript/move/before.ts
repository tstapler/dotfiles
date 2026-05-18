// File: src/services/user.ts (before move)
// This file will be moved to src/core/user.ts

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
