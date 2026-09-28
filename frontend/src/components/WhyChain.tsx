import type { ReactNode } from "react";

export interface WhyStep {
  label: string;
  content: ReactNode;
}

export function WhyChain({ steps }: { steps: WhyStep[] }) {
  return (
    <div className="why-chain">
      {steps.map((s) => (
        <div className="why-step" key={s.label}>
          <div className="label">{s.label}</div>
          <div className="content">{s.content}</div>
        </div>
      ))}
    </div>
  );
}
