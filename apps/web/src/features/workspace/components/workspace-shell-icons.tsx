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

