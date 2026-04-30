import { clsx } from "clsx";
import { forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "hero" | "link";

type ButtonProps = {
  variant?: ButtonVariant;
  as?: "button" | "a";
  href?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement> &
  Pick<React.AnchorHTMLAttributes<HTMLAnchorElement>, "target" | "rel">;

const variantClass: Record<ButtonVariant, string> = {
  primary: "ink-button",
  secondary: "ink-button-secondary",
  danger: "ink-button-danger",
  hero: "ink-button-hero",
  link: "ink-link-button",
};

export const Button = forwardRef<HTMLButtonElement | HTMLAnchorElement, ButtonProps>(
  function Button({ variant = "primary", className, as, href, ...rest }, ref) {
    const classes = clsx(variantClass[variant], className);

    if (as === "a" && href) {
      return (
        <a
          ref={ref as React.Ref<HTMLAnchorElement>}
          href={href}
          className={classes}
          {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}
        />
      );
    }

    return (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        className={classes}
        {...rest}
      />
    );
  },
);
