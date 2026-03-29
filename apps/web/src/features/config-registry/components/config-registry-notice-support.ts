import type { AppNoticeTone } from "@/components/ui/app-notice";

export type ConfigRegistryFeedback = {
  message: string;
  tone: "danger";
};

type ConfigRegistryNotice = {
  content: string;
  title: string;
  tone: AppNoticeTone;
};

export function buildConfigRegistrySaveSuccessNotice(): ConfigRegistryNotice {
  return {
    content: "配置已保存。",
    title: "平台配置",
    tone: "success",
  };
}

export function buildConfigRegistrySaveErrorFeedback(message: string): ConfigRegistryFeedback {
  return {
    message: message.trim(),
    tone: "danger",
  };
}

export function buildConfigRegistrySaveErrorNotice(message: string): ConfigRegistryNotice {
  return {
    content: message.trim(),
    title: "平台配置",
    tone: "danger",
  };
}
