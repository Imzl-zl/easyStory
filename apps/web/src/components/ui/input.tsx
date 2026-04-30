import { clsx } from "clsx";
import { forwardRef } from "react";

type InputVariant = "default" | "roomy";

type InputProps = {
  variant?: InputVariant;
} & React.InputHTMLAttributes<HTMLInputElement>;

const variantClass: Record<InputVariant, string> = {
  default: "ink-input",
  roomy: "ink-input-roomy",
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { variant = "default", className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={clsx(variantClass[variant], className)}
      {...rest}
    />
  );
});

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ className, ...rest }, ref) {
    return (
      <textarea ref={ref} className={clsx("ink-textarea", className)} {...rest} />
    );
  },
);
