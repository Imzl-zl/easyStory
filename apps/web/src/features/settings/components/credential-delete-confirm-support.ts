import type { CredentialView } from "@/lib/api/types";

const DELETE_RULE_ITEM = "如果这条模型连接已经产生用量历史，后端会拒绝删除。";
const DELETE_AUDIT_ITEM = "删除成功后，系统会写入一条删除审计记录。";

export function getCredentialScopeLabel(credential: CredentialView): string {
  return credential.owner_type === "project" ? "项目级模型连接" : "全局模型连接";
}

export function buildCredentialDeleteImpactItems(credential: CredentialView): string[] {
  return credential.owner_type === "project"
    ? buildProjectCredentialDeleteImpactItems(credential)
    : buildUserCredentialDeleteImpactItems(credential);
}

function buildProjectCredentialDeleteImpactItems(credential: CredentialView): string[] {
  const firstItem = credential.is_active
    ? `删除后，项目级连接标识「${credential.provider}」将不再覆盖同标识的全局连接。`
    : "这条连接当前已停用；删除后只会移除项目级记录，不会影响当前已停用状态。";
  return [
    firstItem,
    "如果存在同标识的全局连接，系统会继续使用全局连接；否则只有项目明确允许系统连接池时才会继续往下找。",
    "如果没有可用的替代连接，引用这条连接标识的模型调用会直接失败。",
    DELETE_RULE_ITEM,
    DELETE_AUDIT_ITEM,
  ];
}

function buildUserCredentialDeleteImpactItems(credential: CredentialView): string[] {
  const firstItem = credential.is_active
    ? `删除后，全局连接标识「${credential.provider}」将不再作为默认连接来源。`
    : "这条连接当前已停用；删除后只会移除全局记录，不会影响当前已停用状态。";
  return [
    firstItem,
    "已经配置同连接标识项目级连接的项目不受影响；项目级连接始终优先于全局连接。",
    "没有项目级同标识连接的请求，只有在项目明确允许系统连接池时才会继续往下找；否则会直接失败。",
    DELETE_RULE_ITEM,
    DELETE_AUDIT_ITEM,
  ];
}
