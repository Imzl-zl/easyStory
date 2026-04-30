import { clsx } from "clsx";

type CalloutVariant = "info" | "warning" | "success" | "danger";

type CalloutProps = {
  variant: CalloutVariant;
} & React.HTMLAttributes<HTMLDivElement>;

const variantClass: Record<CalloutVariant, string> = {
  info: "callout-info",
  warning: "callout-warning",
  success: "callout-success",
  danger: "callout-danger",
};

export function Callout({
  variant,
  className,
  ...rest
}: CalloutProps) {
  return (
    <div className={clsx(variantClass[variant], className)} {...rest} />
  );
}
