import type { WorkspaceSegment } from "@/features/workspace/components/workspace-shell-support";

type WorkspaceIconProps = {
  className?: string;
};

export function WorkspaceBrandIcon({ className }: Readonly<WorkspaceIconProps>) {
  return (
    <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24">
      <path d="M5 6.5h14M7 12h10M9 17.5h6" stroke="currentColor" strokeLinecap="round" />
      <path d="M6.5 4.5h11a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z" stroke="currentColor" />
    </svg>
  );
}

export function WorkspaceNavIcon({
  className,
  segment,
}: Readonly<WorkspaceIconProps & { segment: WorkspaceSegment }>) {
  switch (segment) {
    case "lobby":
      return (
        <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24">
          <path d="M4.75 11.5 12 5l7.25 6.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M7.25 10.75V19h9.5v-8.25" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "studio":
      return (
        <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24">
          <path d="M6 5.75h12a1.25 1.25 0 0 1 1.25 1.25v10A1.25 1.25 0 0 1 18 18.25H6A1.25 1.25 0 0 1 4.75 17V7A1.25 1.25 0 0 1 6 5.75Z" stroke="currentColor" />
          <path d="M8 9h8M8 12h8M8 15h5" stroke="currentColor" strokeLinecap="round" />
        </svg>
      );
    case "engine":
      return (
        <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24">
          <path d="M12 5.5v4M12 14.5v4M6.5 12h4M13.5 12h4" stroke="currentColor" strokeLinecap="round" />
          <path d="M12 4.75a7.25 7.25 0 1 1 0 14.5 7.25 7.25 0 0 1 0-14.5Z" stroke="currentColor" />
        </svg>
      );
    case "lab":
      return (
        <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24">
          <path d="M6.5 6.5h11M6.5 12h7M6.5 17.5h4" stroke="currentColor" strokeLinecap="round" />
          <path d="M17.5 15.5a2.75 2.75 0 1 0 0-5.5 2.75 2.75 0 0 0 0 5.5Z" stroke="currentColor" />
        </svg>
      );
    default:
      return assertNever(segment);
  }
}

export function WorkspaceToggleIcon({
  className,
  collapsed,
}: Readonly<WorkspaceIconProps & { collapsed: boolean }>) {
  return (
    <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24">
      <path d={collapsed ? "M9 6.75 14.5 12 9 17.25" : "M15 6.75 9.5 12 15 17.25"} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.25 5.25v13.5" stroke="currentColor" strokeLinecap="round" />
    </svg>
  );
}

export function WorkspaceLogoutIcon({ className }: Readonly<WorkspaceIconProps>) {
  return (
    <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24">
      <path d="M10 6H7.25A1.25 1.25 0 0 0 6 7.25v9.5A1.25 1.25 0 0 0 7.25 18H10" stroke="currentColor" strokeLinecap="round" />
      <path d="M13 8.25 17.25 12 13 15.75" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 12h7" stroke="currentColor" strokeLinecap="round" />
    </svg>
  );
}

function assertNever(value: never): never {
  throw new Error(`Unknown workspace segment: ${value}`);
}
