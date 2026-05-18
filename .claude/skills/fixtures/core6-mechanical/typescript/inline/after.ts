function createUserRecord(name: string, email: string): Record<string, string> {
  const normalizedEmail = email.trim().toLowerCase();
  return { name, email: normalizedEmail };
}

const record = createUserRecord('Alice', '  Alice@Example.COM  ');
console.log(record);
