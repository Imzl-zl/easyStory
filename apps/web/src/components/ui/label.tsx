import { clsx } from "clsx";

type LabelVariant = "default" | "overline";

type LabelProps = {
  variant?: LabelVariant;
  as?: "label" | "span";
} & React.LabelHTMLAttributes<HTMLLabelElement>;

const variantClass: Record<LabelVariant, string> = {
  default: "label-text",
  overline: "label-overline",
};

export function Label({
  variant = "default",
  className,
  as: Tag = "label",
  ...rest
}: LabelProps) {
  return (
    <Tag className={clsx(variantClass[variant], className)} {...rest} />
  );
}
