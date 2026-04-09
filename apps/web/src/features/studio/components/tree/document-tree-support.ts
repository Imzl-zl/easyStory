export function hasSelectedDescendant(nodePath: string, selectedPath: string | null) {
  return selectedPath?.startsWith(`${nodePath}/`) === true;
}

export function resolveInitialNodeExpandedState({
  depth,
  nodePath,
  selectedPath,
}: Readonly<{
  depth: number;
  nodePath: string;
  selectedPath: string | null;
}>) {
  if (depth === 0 && nodePath === "设定") {
    return true;
  }
  return hasSelectedDescendant(nodePath, selectedPath);
}

export function resolveNodeExpandedState({
  collapsedSelectionSignal,
  manualExpanded,
  selectedPath,
  nodePath,
  selectedPathSignal,
}: Readonly<{
  collapsedSelectionSignal: symbol | null;
  manualExpanded: boolean;
  selectedPath: string | null;
  nodePath: string;
  selectedPathSignal: symbol;
}>) {
  return (
    manualExpanded ||
    (hasSelectedDescendant(nodePath, selectedPath) && collapsedSelectionSignal !== selectedPathSignal)
  );
}
