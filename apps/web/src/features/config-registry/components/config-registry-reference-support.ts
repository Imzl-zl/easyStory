export type ConfigRegistryReferenceOption = {
  label: string;
  value: string;
};

export type ConfigRegistryReferenceFieldState = {
  bannerMessage: string | null;
  bannerTone: "danger" | "muted" | null;
  emptyMessage: string;
  options: ConfigRegistryReferenceOption[];
};

export function buildConfigRegistryReferenceFieldState({
  defaultEmptyMessage,
  errorMessage,
  loadingMessage,
  isLoading,
  options,
}: Readonly<{
  defaultEmptyMessage: string;
  errorMessage: string | null;
  loadingMessage: string;
  isLoading: boolean;
  options: ConfigRegistryReferenceOption[];
}>): ConfigRegistryReferenceFieldState {
  if (errorMessage) {
    return {
      bannerMessage: options.length > 0 ? errorMessage : null,
      bannerTone: options.length > 0 ? "danger" : null,
      emptyMessage: errorMessage,
      options,
    };
  }
  if (isLoading) {
    return {
      bannerMessage: options.length > 0 ? loadingMessage : null,
      bannerTone: options.length > 0 ? "muted" : null,
      emptyMessage: loadingMessage,
      options,
    };
  }
  return {
    bannerMessage: null,
    bannerTone: null,
    emptyMessage: defaultEmptyMessage,
    options,
  };
}
