# Hermes Skills（本專案內建）

此目錄包含與 `wnacg-downloader-cli` 搭配使用的 **Hermes Agent Skills**，提供引導式工作流程與快速上手範例。

## 已內建 Skills

| Skill | 說明 |
|-------|------|
| `wnacg-hermes-guided-recovery` | 5 步驟精準恢復 pipeline（清單 → 搜尋關鍵字判斷 → Python 搜尋 → 目標判斷 → 下載） |

## 快速上手範例

| 範例 | 說明 |
|------|------|
| `examples/search-and-download.md` | 搜尋 + 下載單本漫畫，含 agent 輸出解析 |
| `examples/batch-from-list.md` | 從 ID 清單批量恢復，含完整後處理流程 |

## 使用方式

將此目錄下的 skill 載入到你的 Hermes Agent：

```bash
# 複製到 Hermes skills 目錄
cp -r skills/wnacg-hermes-guided-recovery ~/.hermes/skills/
cp -r skills/examples ~/.hermes/skills/wnacg-examples/   # 可選

# 或在 Hermes 對話中直接載入
# skill_view(name='wnacg-hermes-guided-recovery')
```

## 與 CLI 工具整合

所有範例都基於 `wnacg-downloader-cli` 工具的命令：

```bash
cd /home/tsengagent/Nextcloud/Project/tools_工具開發/wnacg-downloader-cli
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg --help
```

詳細使用說明請見專案 [README.md](../README.md)。
