# Synthesizer 探索 Findings

跑 DeepEval `Synthesizer.generate_goldens_from_scratch` 一次，產出 15 條 LLM-authored query（檔案 `2026-04-26T043102Z.json`，gitignored）。底下從四個維度評估「能不能直接補進 production validation set」。

**結論先講**：**不能直接用**。LLM 生出來的題對於建構結構化的 GitHub 工具呼叫 eval 來說 scope 偏移、多樣性不足、leakage 風險高、fit 度低。但作為「對照組」很有意義——直接證明手動 + Claude Code co-design 的策略確實必要。

---

## 1. GitHub scope 符合度

**符合度約 8/15（53%）**。一半的生成題目偏離了「呼叫 GitHub REST API 工具」的範圍，落在抽象戰略推理、生態系趨勢 inference 那種 essay 題。

**符合 scope 的例子**（可以直接 map 到 13 個 tool）：

> [2] Compare `kubernetes/kubernetes` latest stable vs. pre-releases.
> → 對應 `list_releases` × 1，乾淨明確

> [4] Compare top contributors to 'tensorflow/tensorflow' vs 'pytorch/pytorch'.
> → 對應 `list_contributors` × 2，簡單對比題

**偏離 scope 的例子**（沒辦法用工具回答）：

> [11] Infer broader tech shifts from this week's trending OSS projects.
> → GitHub REST API **沒有** trending endpoint（這是我們 README 已記錄的 §2 不可解限制），且「broader tech shifts」是社論題不是查詢題

> [13] Deduce Google's strategic tech priorities from its Java OSS repos.
> → 「strategic priorities」屬於商業分析，不是 GitHub 資料能直接答的

LLM 在「生成自然語言 query」這個 task 上會自然把題目寫得很學術化（"Assess", "Deduce", "Infer broader shifts"），跟真實開發者隨手丟到 CLI 的 query（「axios 之前好像出過事？」「我用 drizzle 一直 drop FK 怎麼辦？」）落差很大。

---

## 2. 多語言覆蓋

**完全 0/15 非英語題**——15 條全部是英文。

手動的 30 題刻意配了 6 種非英語（韓 / 德 / 越 / 日 / 泰 / 西），用來壓測「prompt 規則：不論 query 語言都要呼叫工具」。Synthesizer 用單一 LLM 生題沒有這個 diversity 機制——主流 LLM 在沒明確指示時會預設用英文。

要補多語言只能：
1. 對 styling_config 額外指定語言要求
2. 跑多次 synthesizer 各設一種語言

兩者都需要人類加 metadata，等於把 manual curation 的成本疊加上 LLM 生題的成本，沒比較划算。

---

## 3. Eval-leakage 風險

**風險明顯**。我們的 Synthesizer 跟 judge / 部分 under-test model 共用同一個 model family：

| 角色 | Model |
|---|---|
| Synthesizer（生 query） | `gemini-2.5-flash` |
| 語意 judge | `gemini-2.5-flash` |
| Under-test 之一 | `gemini-3-flash-preview`（同 family） |

如果用 LLM 生的 query + LLM 生的 expected_output 跑 eval：
- Gemini judge 會傾向把 Gemini 自己風格的答案判高分
- Gemini 3 Flash 跑同個 query 也會出類似回答（同 family 同訓練分佈），結構上「自己跟自己對答案」

具體例子：

> [8] Compare 'golang/go' vs 'rust-lang/rust' release cadence ... since 2023.

這題 Gemini 生出來，expected_output 也由 Gemini 生，當 Gemini 3 Flash 答這題時很可能輸出跟 expected_output 高度相似的措辭——eval 看起來分數很高，但其實是 model family 自我增強。

**手動 + Claude Code co-design** 的人類負責真實場景 grounding（axios 事件是真的、drizzle FK 問題是真的），AI 只負責 diversity audit 跟措辭多樣化，避免這類迴圈污染。

---

## 4. 是否能直接補進 production validation set

**不能**。理由整合上面三點 + 兩個額外觀察：

**(a) 引用了不存在的 GitHub 路徑**：
> [3] Contrast open issue counts and avg resolution times for 'ms/vscode' vs. 'ms/typescript'.

`ms/vscode` 不是真實 GitHub 路徑（正確是 `microsoft/vscode`）。Model 拿到這題會在 `search_repositories` 找不到，最後幻想或拒絕——這不是測 model 能力，是測 model 怎麼處理「使用者打錯字」，但又不像我們手動的 `typo`（`gema2` → `gemma2`）那樣有明確 ground truth。

**(b) 結構過於模糊難以判分**：
> [5] Compare 'react' vs. 'vue' repos: name match, >1k stars, and avg. commit freq.

「name match」是什麼意思？「avg. commit freq」要哪個時間區間？沒指定 owner（react 是 facebook/react？vuejs/vue？）。手動寫 GT 要耗大量時間補 unstated assumption；不如直接手寫一條 query 還快。

---

## 一句話總結

**Synthesizer 自動生題對需要「結構化、多語言、grounded 在真實事件」的 NL→tool 場景不適用**。它生出來的東西更像 essay topic 不是真實 dev query。我們維持手動 + Claude Code co-design 的決策被這次探索證明是對的——但探索本身有價值，下次若要擴 validation set 才知道哪些坑要避開。
