// テンプレート保存（chrome.storage.local、Chromeプロファイルごと）
const STORAGE_KEY = "kuukinittei_templates";

export const DEFAULT_TEMPLATES = {
  booking_dm:
    "返信ありがとうございます！\n" +
    "では、こちらのリンクからお願いいたします！\n\n" +
    "日時: {datetime}\n" +
    "リンク: {link}",
  suggest_dm:
    "以下の日程が空いております！\n" +
    "こちらの日程のご都合はいかがでしょうか✨\n\n" +
    "{slots}",
};

export function loadTemplates() {
  return new Promise((resolve) => {
    chrome.storage.local.get([STORAGE_KEY], (result) => {
      const saved = result[STORAGE_KEY] || {};
      resolve({
        booking_dm:
          typeof saved.booking_dm === "string" && saved.booking_dm
            ? saved.booking_dm
            : DEFAULT_TEMPLATES.booking_dm,
        suggest_dm:
          typeof saved.suggest_dm === "string" && saved.suggest_dm
            ? saved.suggest_dm
            : DEFAULT_TEMPLATES.suggest_dm,
      });
    });
  });
}

export function saveTemplates(templates) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ [STORAGE_KEY]: templates }, resolve);
  });
}

export function resetTemplates() {
  return new Promise((resolve) => {
    chrome.storage.local.remove([STORAGE_KEY], resolve);
  });
}

// {key} を vars[key] で置換。vars にないキーはそのまま残す。
export function safeFormat(template, vars) {
  return template.replace(/\{(\w+)\}/g, (m, key) =>
    vars[key] !== undefined && vars[key] !== null ? vars[key] : m
  );
}
