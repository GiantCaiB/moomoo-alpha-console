import { clsx } from "clsx";

interface GlassyCardProps {
  children: React.ReactNode;
  className?: string;
  neon?: "green" | "red" | "none";
  title?: string;
  action?: React.ReactNode;
}

export default function GlassyCard({
  children,
  className,
  neon = "none",
  title,
  action,
}: GlassyCardProps) {
  return (
    <div
      className={clsx(
        "glassy p-5",
        neon === "green" && "neon-border",
        neon === "red" && "neon-border-red",
        className
      )}
    >
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          {title && (
            <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
              {title}
            </h3>
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
