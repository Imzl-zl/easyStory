import { clsx } from "clsx";

type IconButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

export function IconButton({ className, ...rest }: IconButtonProps) {
  return (
    <button className={clsx("ink-icon-button", className)} {...rest} />
  );
}
