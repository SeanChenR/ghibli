# Mission — ghibli

## 專案名稱

**ghibli**（GitHub Intelligence Bridge）

## 核心使命

讓任何人都能用自然語言查詢 GitHub，不需要記住 API 端點格式或查詢參數語法。

ghibli 作為人與 GitHub REST API 之間的智慧橋樑，透過 LLM 解析使用者意圖，自動生成並執行對應的 API 請求，最終以易讀的格式呈現結果。

## 核心流程

```
開啟 Session
     ↓
自然語言輸入 → Gemini（帶 GitHub tools）→ Function Calling → GitHub REST API
     ↑                                          ↓
     └──────────── 多輪對話 ───────────── 格式化輸出
```

支援多輪對話：使用者可以追問、細化查詢，Gemini 自行決定是否呼叫 API 及呼叫幾次。每次對話以 Session 形式儲存於 `~/.ghibli/sessions.db`。

## 目標使用者

- **開發者**：想快速查詢 GitHub 資料，不想查文件也不想手刻 curl
- **不熟悉 API 的使用者**：只知道想要什麼，不知道怎麼問
- **多語言使用者**：能用繁體中文或英文輸入，不限語言

## 價值主張

| 傳統方式 | ghibli |
|---|---|
| 查 GitHub API 文件 | 直接描述需求 |
| 手刻 curl / 寫腳本 | 一句話完成 |
| 只能用英文 | 中文、英文都行 |
| 固定格式查詢 | 模糊表達也能處理 |

## 長期願景

ghibli 不只是一個 CLI 工具，更是一個 **NL-to-API 的多模型評測基準平台**。

透過累積高品質的自然語言查詢資料集與 ground truth，ghibli 可以評測不同 LLM（開源、閉源）在「將自然語言轉換為結構化 API 請求」這個任務上的表現，為模型選型提供實證依據。
