interface LoadingProps {
  text?: string;
}

export function Loading({ text = "Загрузка..." }: LoadingProps) {
  return (
    <div className="loading">
      <div className="spinner" />
      <span>{text}</span>
    </div>
  );
}
