# Agent Skills（本專案內建）

此目錄包含與 `wnacg-downloader-cli` 搭配使用的 **Agent Skill**，提供引導式搜尋下載流程與快速上手範例。

## 已內建 Skill

| Skill | 說明 |
|-------|------|
| `wnacg-search-download` | 通用「搜尋 → 判斷目標 → 下載 → 匯出」流程，含關鍵字設計、目標驗證、限速可靠性指引 |

## 快速上手範例

| 範例 | 說明 |
|------|------|
| `examples/search-and-download.md` | 搜尋 + 下載單本，含 agent 輸出解析 |
| `examples/batch-from-list.md` | 從 ID 清單批量下載 |

## 使用方式

將此目錄下的 skill 載入到你的 agent，或在對話中直接載入：

```bash
# 複製到 agent 的 skills 目錄（路徑依你的 agent 而定）
cp -r skills/wnacg-search-download <your-agent-skills-dir>/

# 或在對話中載入
# skill_view(name='wnacg-search-download')
```

## 與 CLI 工具整合

所有範例都基於 `wnacg` 命令：

```bash
cd /path/to/wnacg-downloader-cli
uv run wnacg --help
```

詳細使用說明請見專案 [README.md](../README.md)。
</content>
