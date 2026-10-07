# goal-checkpoint

長期のgoal開発で、局所改善が続く一方でマイルストーンが進まない状態を見つける、ローカルCodex用プラグインです。3時間経過後の次の対応hookイベントで再評価を促し、完了条件の証拠と次の具体的な実装を確認します。

## 使い方

インストール後、同梱 `goal-checkpoint` Skillへ次のように依頼します。

- `goal-checkpoint enable`：現在のgoal・計画・実装からbaselineを作り、監視を有効化。
- `goal-checkpoint status`：監視の状態、マイルストーン、次の期限、未点検を確認。
- `goal-checkpoint review`：期限を待たず現在の進捗を点検。
- `goal-checkpoint disable`：監視を解除。
- `goal-checkpoint resume`：最新goalを確認して新しいbaselineから再開。

goalツールがある場合はactiveなgoalが必要です。インストールしただけでは全チャットを監視しません。goalの新規作成や別チャットへの引継ぎも自動で行いません。

Python 3.9以上、macOS/Linux、ローカルCodexのcommand hookが必要です。状態はランタイム提供の、このpluginの `PLUGIN_DATA` 配下だけに保存します。hookへ渡される環境変数が通常のツールにも渡されるとは限らないため、インストール時に実際のdataディレクトリを確認し、Skillのコマンド実行にも同じ `PLUGIN_DATA` を指定してください。未確認のパスは使いません。dataディレクトリはランタイム側で用意されている必要があります。

## 動作

`SessionStart`、`UserPromptSubmit`、対応するツールの `PostToolUse`、`Stop` で期限を確認します。未点検のまま終了する場合は `Stop` が当該turnを一度だけ継続します。ユーザーが割り込むと当該turnの継続を抑止し、次の指示で未点検を回収します。

通知と点検完了を分け、点検後のackから次の3時間を測ります。休止分の通知をまとめて発火させません。無操作中や長い単一ツール実行中に、正確な時刻で発火するタイマーではありません。

再評価は編集数やコミット数ではなく、完了条件を満たした証拠と阻害要因の減少で判定します。必要な安全修正も進捗として扱い、goalの完了・停止・予算終了では開発を再開しません。詳細は [Skill](skills/goal-checkpoint/SKILL.md) を参照してください。

状態確認は短い同期処理で、handler timeoutは2秒、Interruptは1秒です。エラー時はツール結果を拒否せず監視失敗を知らせます。hook出力は固定の指示と発火IDだけで、goal・文書本文・ツール結果・認証情報を再掲しません。

## 検証と導入状態

```sh
python3 -B -m unittest discover -s plugins/goal-checkpoint/tests -v
```

上記はrepository rootで実行します。テストは隔離した一時ディレクトリに状態を作り、3時間境界、pending/ack、再開、割込み、排他、破損、symlink、hook JSON入出力を確認します。host timeoutの確認はsubprocessによる合成検証です。

source作成、installed/trusted、live delivery verifiedは別の状態です。このプラグインのsourceにはhook設定を含みますが、インストールやhookの信頼承認を自動で済ませません。数日の実運用で改善したという測定結果はありません。

公式資料：[Hooks](https://learn.chatgpt.com/docs/hooks)、[Plugin packaging](https://developers.openai.com/plugins/build/plugins)。
