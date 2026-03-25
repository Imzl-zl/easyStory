import type { CredentialView } from "@/lib/api/types";

const DELETE_RULE_ITEM = "若该凭证已有 token usage 历史，后端会拒绝删除。";
const DELETE_AUDIT_ITEM = "删除成功后，系统会写入一条 credential_delete 审计事件。";

export function getCredentialScopeLabel(credential: CredentialView): string {
  return credential.owner_type === "project" ? "项目级凭证" : "全局凭证";
}

export function buildCredentialDeleteImpactItems(credential: CredentialView): string[] {
  return credential.owner_type === "project"
    ? buildProjectCredentialDeleteImpactItems(credential)
    : buildUserCredentialDeleteImpactItems(credential);
}

function buildProjectCredentialDeleteImpactItems(credential: CredentialView): string[] {
  const firstItem = credential.is_active
    ? `删除后，项目级 provider「${credential.provider}」将不再覆盖同 provider 的全局凭证。`
    : "当前凭证已停用；删除只会移除项目级记录，不会成为当前运行时的活动凭证来源。";
  return [
    firstItem,
    "若存在已启用的全局同 provider 凭证，运行时会回退到全局凭证；否则仅在项目显式允许系统凭证池时才会继续解析到系统级。",
    "若不存在可用回退凭证，引用该 provider 的模型调用会因找不到可用凭证而失败。",
    DELETE_RULE_ITEM,
    DELETE_AUDIT_ITEM,
  ];
}

function buildUserCredentialDeleteImpactItems(credential: CredentialView): string[] {
  const firstItem = credential.is_active
    ? `删除后，全局 provider「${credential.provider}」将不再作为该渠道的默认凭证来源。`
    : "当前凭证已停用；删除只会移除全局记录，不会成为当前运行时的活动凭证来源。";
  return [
    firstItem,
    "已配置同 provider 项目级凭证的项目不受影响；项目级始终优先于全局。",
    "未配置项目级同 provider 凭证的请求，只有在项目显式允许系统凭证池时才会继续解析到系统级；否则会因找不到可用凭证而失败。",
    DELETE_RULE_ITEM,
    DELETE_AUDIT_ITEM,
  ];
}
