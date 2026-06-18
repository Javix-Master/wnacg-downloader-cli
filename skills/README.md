# Hermes Skills（本專案內建）

此目錄包含與本 CLI 工具搭配使用的 **Hermes Agent Skills**，提供引導式工作流程。

## 已內建 Skills

| Skill | 說明 |
|-------|------|
| `wnacg-hermes-guided-recovery` | Hermes 引導式 wnacg 漫畫恢復流程 — 5 步驟精準 pipeline（清單標題 → Hermes 判斷搜尋關鍵字 → Python 搜尋 → Hermes 判斷目標 → Python 下載） |

## 使用方式

將此目錄下的 skill 載入到你的 Hermes Agent：

```bash
# 複製到 Hermes skills 目錄
cp -r skills/wnacg-hermes-guided-recovery ~/.hermes/skills/

# 或在 Hermes 對話中直接載入
# 使用 skill_view(name='wnacg-hermes-guided-recovery')
```

詳細流程請見各 skill 的 `SKILL.md` 及內附 references。
