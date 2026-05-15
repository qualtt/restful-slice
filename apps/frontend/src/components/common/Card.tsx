import type { PropsWithChildren } from "react";
import clsx from "clsx";

interface CardProps extends PropsWithChildren {
  className?: string;
  title?: string;
}

export function Card({ className, title, children }: CardProps) {
  return (
    <section
      className={clsx(
        "window-2002 flex flex-col text-black",
        className
      )}
    >
      {title && <div className="window-title-2002">{title}</div>}
      <div className="p-3">{children}</div>
    </section>
  );
}
