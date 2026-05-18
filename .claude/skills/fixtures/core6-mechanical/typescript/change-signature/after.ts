interface RequestOptions {
  timeout?: number;
  retries?: number;
}

function fetchData(url: string, options?: RequestOptions): Promise<string> {
  return Promise.resolve(`data from ${url}`);
}

async function main(): Promise<void> {
  const result1 = await fetchData('https://api.example.com/users');
  const result2 = await fetchData('https://api.example.com/posts');
  const result3 = await fetchData('https://api.example.com/comments');
  console.log(result1, result2, result3);
}

main();
