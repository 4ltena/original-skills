---
metadata:
  author: "4ltena"
  version: "1.1"
name: grilling
description: "重大な未決定の設計判断を依存順に詰める。通常の実装判断や既に承認済みの選択は除く。"
---

# 判断を詰める

決定を依存関係の木にし、前提が決まった問いだけを一巡にまとめ、推奨と理由を添えて回答を待つ。回答で次の問いを組み替え、未回答の前提に依存する問いは後へ回す。

事実は調査し、利用者には好み・制約・採否を聞く。委譲可能な独立調査の間も依存しない判断を進める。未提供のツールを想定せず、認知負荷を抑える。見ないと決まらないUIは `ux-spike` へ。

重大な未確定事項がなくなれば合意を短く示す。文書化・実装は `spec-first-development` に従い、このスキルではファイルを書かない。

出典：`~/.claude/skills/grilling/SKILL.md` のCodex向け再構成。
元の方法：mattpocock/skills の grilling（MIT、Matt Pocock / aihero.dev）。
