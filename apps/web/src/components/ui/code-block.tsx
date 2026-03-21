type CodeBlockProps = {
  value: unknown;
};

export function CodeBlock({ value }: CodeBlockProps) {
  return <pre className="mono-block">{JSON.stringify(value, null, 2)}</pre>;
}
