interface User {
  email: string;
  age: number;
}

function processUserRegistration(user: User): string {
  // Validation block — candidate for extraction
  if (!user.email.includes('@')) {
    throw new Error('Invalid email: missing @');
  }
  if (user.email.length < 5) {
    throw new Error('Invalid email: too short');
  }
  if (user.age < 18) {
    throw new Error('User must be at least 18 years old');
  }

  // Registration logic
  const userId = `user_${Date.now()}`;
  console.log(`Registered user ${user.email} with id ${userId}`);
  return userId;
}

const newUser: User = { email: 'test@example.com', age: 25 };
const id = processUserRegistration(newUser);
console.log(id);
