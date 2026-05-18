function formatUserEmail(email: string): string {
  return email.trim().toLowerCase();
}

function createUserRecord(name: string, email: string): Record<string, string> {
  const normalizedEmail = formatUserEmail(email);
  return { name, email: normalizedEmail };
}

const record = createUserRecord('Alice', '  Alice@Example.COM  ');
console.log(record);
