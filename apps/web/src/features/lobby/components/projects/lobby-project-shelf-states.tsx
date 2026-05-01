import { getErrorMessage } from "@/lib/api/client";

export function ProjectShelfLoadingState() {
  return (
    <div className="lobby-shelf-loading">
      <div className="lobby-shelf-loading__spinner" />
      <p className="lobby-shelf-loading__text">整理书卷中...</p>
    </div>
  );
}

export function ProjectShelfErrorState({ error }: { error: unknown }) {
  return <div className="lobby-shelf-error">{getErrorMessage(error)}</div>;
}

export function ProjectShelfEmptyState({
  deletedOnly,
}: {
  deletedOnly: boolean;
}) {
  return (
    <div className="lobby-shelf-empty">
      <div className="lobby-shelf-empty__glow">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--text-tertiary)"
          strokeWidth="1"
          strokeLinecap="round"
        >
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
      </div>
      <h3 className="lobby-shelf-empty__title">
        {deletedOnly ? "回收站为空" : "书阁尚空"}
      </h3>
      <p className="lobby-shelf-empty__desc">
        {deletedOnly
          ? "当前没有已删除项目。删除后的项目会保留在回收站里，随时可以恢复。"
          : "书阁尚空，创建第一卷开始你的创作之旅。"}
      </p>
    </div>
  );
}
