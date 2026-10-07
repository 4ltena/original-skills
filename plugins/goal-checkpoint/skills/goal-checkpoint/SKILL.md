---
name: goal-checkpoint
description: "長期のgoal開発で3時間ごとに完了条件と実装進捗を再評価し、局所改善の繰り返しからマイルストーンを進める。監視の有効化・状態確認・再評価・無効化・再開に使用する。goalの新規作成や全体監査には使わない。"
---

# goal-checkpoint

数日続く開発で、作業量だけ増えてマイルストーンが進まない状態を見つける。hookは期限とpendingを管理し、このSkillがgoalと実装を評価する。点検を終えたら、承認済みの作業へ戻る。

## 操作と前提

`enable`、`status`、`review`、`disable`、`resume` を受け付ける。長期開発の監視依頼、または有効なnative goalに沿った長期開発で `enable` を使う。pluginが存在するだけでは全チャットを監視しない。

状態コマンドは、このSkillのディレクトリから見て `../../scripts/checkpoint.py`。インストール先の絶対パスを確認して実行する。Python 3.9以上、macOS/LinuxのローカルCodexを対象とする。

- sessionは実行環境の `CODEX_THREAD_ID` を使う。なければランタイムから確認したsessionを `--session` に渡す。名前・cwdから推測しない。
- 書込み先はこのpluginの実際の `PLUGIN_DATA` だけ。hook環境にはランタイムが提供するが、通常のツール環境にも提供されるとは限らない。ツール環境にない場合は、インストール時に確認した実際のruntime dataディレクトリを実行環境へ明示して使う。パスを推測したり、別homeへfallbackしたりしない。未確認なら有効化失敗を報告し、監視中と表示しない。
- goalがないときは有効化しない。goalツール自体がない環境では、ユーザーが明示した目的と既存計画を使った手動監視を選べる。Skillだけを根拠にgoalを作成しない。
- goal状態、予算、操作権限は既存ルールに従う。このSkillはpause、blocked、completeの条件を緩めない。

## enable / resume

1. 利用可能な `get_goal` で現在のobjective・状態・残予算を確認する。active以外、予算終了、ユーザーの停止指示がある場合は有効化しない。
2. `docs/superpowers/CURRENT.md`、なければroot `CURRENT.md`、なければ既存handoffを読み、関連する現在の仕様・計画と照合する。監視workspace、現在のマイルストーン、完了条件、baselineの実装・検証証拠を確定する。証拠がない項目は未確認とする。
3. `enable` または `resume` に次のJSONをstdinで渡す。文字列は各2KiBまで、全体16KiBまで。目的の全文やtranscriptは保存せず、短い参照と必要な事実を使う。

```json
{
  "goal_status": "active",
  "budget_exhausted": false,
  "goal_ref": "native:確認済みのgoal識別子",
  "milestone": "現在のマイルストーン識別子",
  "criteria": "承認済みの完了条件と参照先",
  "evidence": "現状の実装・検証証拠の参照、未確認事項"
}
```

状態コマンドは `python3 <確認済みscript絶対パス> enable --workspace <確認済みworkspace絶対パス>` の形。stdinは構造化ツール引数または引用したheredocで渡し、文書内容をshellコードに補間しない。`resume` は既存の登録workspaceを使い、新しい世代とbaselineを作る。

native goalに永続IDがない場合は、今回の有効化用にUUIDを生成した `native:<UUID>` を参照として使う。その参照はplugin監視の識別子であり、native goalのIDとは報告しない。objectiveの一致だけで別goalを同一視しない。目的の変更やgoalの置換を認識したら新たに `enable` する。置換の有無を確認できない場合は不明を伝え、連続性を断定しない。

コマンド成功後に結果を読み、有効／無効、milestone、due_at（UTC epochからユーザーのtimezoneへ変換）、pendingの有無を短く報告する。起動成功だけでhook配信確認済みとしない。別sessionへ自動引継ぎしない。

## review

hookから発火ID付きの点検要求が届いたとき、またはユーザーが手動点検を求めたときに実行する。点検は現在の完了条件に絞る。既存仕様を作り直したり、全体監査を始めたりしない。

1. **先に最新goalと停止指示を確認する。** goal完了、pause、blocked、予算終了、ユーザーの停止なら `disable` して終了し、開発を再開しない。最新goalを取得できなければactiveのackをせず、未確認の理由を伝える。
2. `status` を実行し、workspace、generation、baseline、pending、stalled_countを読む。通知の発火IDと現在のpendingが一致しなければ古い通知として現在状態を使う。手動点検でpendingがなければ、状態コマンドの `review` を呼んでpendingを作る。監視が無効なら勝手に再開しない。
3. 現在のCURRENT・関連計画、実装、必要な検証証拠をbaselineと比較する。完了条件を満たした証拠、残る条件、未確認を分ける。変更量、コミット数、テスト数、レビュー指摘数だけを進捗にしない。
4. 未達条件や具体的な阻害要因が減っているなら `progress`。周辺改善や同じ調査・レビュー・再テストだけで、未達条件も阻害要因も減っていなければ `stalled`。達成済みmilestoneの次は既存計画に沿って選び、goal全体の未達条件を確認する。
5. `stalled` なら原因を示し、完了条件に関係しない改善を後回しにして、条件を満たす最小の実装と確認を次に選ぶ。必要な不具合修正・安全条件・回復処理・依存解消は進捗に含め、速度のために捨てない。
6. 今回も同じmilestone・完了条件で `stalled`、かつ前回のstalled_countが1以上なら連続停滞。既に進まなかった手順を理由なく選び直さず、具体的な別の進め方か必要なユーザー判断を示す。点検後は承認済み範囲の実装へ戻る。目的・完了条件・権限を変える必要がある場合だけ承認を求める。

結果は「最新goal状態／milestone／前回からの証拠／判定と理由／次の具体的な作業／ackまたは解除」の6項目を短く示す。必要なら既存CURRENTの進捗を更新する。新しいプロジェクト進捗台帳は作らない。

activeの点検を終えたら `ack` を実行する。enableのJSONに、statusで確認した `generation`、`checkpoint_id`（現在pendingのid）、`verdict`（`progress` / `stalled`）を追加し、証拠・milestoneを最新にする。次の検証をまだ実行していなくても、点検自体が終わり未確認を正確に記録したならackできる。ackを実装やgoalの完了証明と扱わない。コマンドの成功とpending消去を確認してから完了と報告する。

## status / disable / 回復

- `status` は読み出した状態を表示する。有効／無効、milestone、期限、pendingを区別する。未登録・破損・環境不足を監視中と報告しない。
- `disable` はstdinに `{"reason":"確認済みの停止理由"}` を渡す。goal状態そのものは変更しない。明示停止やgoalの終了状態で使う。
- `Interrupt` は当該turnの継続だけを抑止し、監視・pendingは残る。次のユーザー指示に従い回収する。中断を無効化の意思と推測しない。
- 状態破損は `status` で確認し、最新goalとbaselineを取得して明示的な `enable` で新世代を作る。古いack、symlink、他所有者の状態は強制上書きしない。
- 3時間はenableまたはackからの経過時間。期限後の次の対応イベントで一度発火する。無操作中、長い単一ツール実行中の厳密な定時起動は保証しない。再開・圧縮は同じ状態を使い、未点検を完了扱いしない。
