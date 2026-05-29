type DisclaimerBlockProps = {
  text: string;
};

export function DisclaimerBlock({ text }: DisclaimerBlockProps) {
  return (
    <div className="disclaimer-block">
      <strong>Важно:</strong> {text}
    </div>
  );
}
