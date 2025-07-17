function Loading({ text = "Thinking..." }: { text?: string }) {
  return (
    <div className="text-muted-foreground flex items-center gap-1">
      {[0, 0.2, 0.4].map((delay) => (
        <div
          key={delay}
          className="h-2 w-2 animate-pulse rounded-full bg-current"
          style={delay ? { animationDelay: `${delay}s` } : undefined}
        />
      ))}
      <span className="ml-2 text-sm">{text}</span>
    </div>
  );
}

export { Loading };
