export function parseFrontmatterBlockValue(
  lines: string[],
  startIndex: number,
  baseIndent: number,
  marker: string,
  label: string,
): {
  nextIndex: number;
  value: string;
} {
  const blockLines: string[] = [];
  let index = startIndex;
  while (index < lines.length) {
    const line = lines[index] ?? "";
    if (!line.trim()) {
      blockLines.push("");
      index += 1;
      continue;
    }
    if (countLeadingSpaces(line) < baseIndent) {
      break;
    }
    blockLines.push(line.slice(baseIndent));
    index += 1;
  }
  if (blockLines.length === 0) {
    throw new Error(`${label} 需要至少一行内容。`);
  }
  return {
    nextIndex: index,
    value: normalizeBlockScalarValue(blockLines, marker),
  };
}

export function hasIndentedChildLine(line: string, indent: number) {
  return Boolean(line.trim()) && countLeadingSpaces(line) >= indent;
}

export function isFrontmatterBlockScalarMarker(value: string) {
  return /^[|>][-+]?$/u.test(value);
}

function normalizeBlockScalarValue(lines: string[], marker: string) {
  if (marker.startsWith("|")) {
    return lines.join("\n");
  }
  return foldBlockScalarLines(lines);
}

function foldBlockScalarLines(lines: string[]) {
  const result: string[] = [];
  let paragraph: string[] = [];
  lines.forEach((line) => {
    if (!line) {
      flushFoldedParagraph(result, paragraph);
      paragraph = [];
      result.push("");
      return;
    }
    paragraph.push(line);
  });
  flushFoldedParagraph(result, paragraph);
  return result.join("\n");
}

function flushFoldedParagraph(result: string[], paragraph: string[]) {
  if (paragraph.length > 0) {
    result.push(paragraph.join(" "));
  }
}

function countLeadingSpaces(line: string) {
  const trimmed = line.trimStart();
  return line.length - trimmed.length;
}
