---
title: "MCPサーバー"
description: "PERT、モンテカルロ、TCO、EVMといった定番のPMO意思決定ツールをClaudeから呼び出せます。インストールはコマンド一つ：uvx pmorun-mcp。"
order: 2
---

## MCPサーバーとは

`pmorun-mcp`は、pmo.runの意思決定ロジック（PERT、モンテカルロ、TCO、EVM）を[Model Context Protocol](https://modelcontextprotocol.io/)経由でLLMから呼び出せるツールとして公開するサーバーです。AirtableやGitHub、スプレッドシートといったデータソースと一緒にClaudeへ接続すれば、Claudeが実際のプロジェクト記録を取得し、計算を実行し、結果を解説してくれます。暗算で済ませるのではなく。

計算の中身は[ロジックAPI](/ja/docs/api-overview/)を支えているMITライセンスのコアと同一です。情報源は一つ、検証モデルも共通です。

## 四つのツール

ツール名は頭字語ではなく、答えるべき意思決定の問いに沿って付けています。Claudeが目的でツールを選べるようにするためです。

| ツール | 意思決定の問い |
|--------|----------------|
| `estimate_task_duration` | 三点見積もりと既知の摩擦要因を踏まえると、このタスクはどれくらいかかるか？ |
| `identify_schedule_risk` | このタスクネットワーク全体では、どれくらいかかりそうか？　リスクを左右するタスクはどれか？ |
| `compare_investment_options` | 候補のベンダーやプラットフォームのうち、実質的な生涯コストで最も安いのはどれか？ |
| `evaluate_project_health` | PV / EV / AC / BACから見て、プロジェクトは順調か、要注意か、危険域か？ |

## インストール

最短の方法は、恒久的なインストールなしでサーバーを動かすことです。`uvx`が[PyPI上の`pmorun-mcp`](https://pypi.org/project/pmorun-mcp/)を使い捨て環境に取得します：

```bash
uvx pmorun-mcp           # 最新リリース
uvx pmorun-mcp@0.2.0     # このリリースに固定（推奨）
```

`@0.2.0`で固定すると、不変のPyPI成果物から再現性のあるインストールになります。固定を外せば常に最新を追従します。

恒久的に入れたい場合は、`uv pip install "pmorun-mcp==0.2.0"`（または通常の`pip install "pmorun-mcp==0.2.0"`）で`pmorun-mcp`コマンドが使えるようになります。

## Claudeへの接続

Claude Codeなら一行です：

```bash
claude mcp add pmo-logic -- uvx pmorun-mcp@0.2.0   # @0.2.0 を外せば最新を追従
```

Claude Desktopの場合は、`claude_desktop_config.json`に以下を追加します：

```json
{
  "mcpServers": {
    "pmo-logic": {
      "command": "uvx",
      "args": ["pmorun-mcp@0.2.0"]
    }
  }
}
```

再起動すると、`pmo-logic`サーバーの下に四つのツールが現れます。

## 実際の問いを投げる

接続が済めば、JSONを書く代わりに質問を投げるだけです。まずは単一のタスクから：

> 「データ移行は、うまくいけば2日、普通なら5日、レガシースキーマが牙を剥けば14日。何日で計画すべきか」

Claudeが`estimate_task_duration`を呼び出し、三点見積もりに対してPERTの計算を実行し、期待値**6.0日**（標準偏差2.0）と答えます。勘ではなく、根拠を示せる一つの数字です。

次に、計画全体へ広げます：

> 「移行タスク全体の三点見積もりと依存関係はこの通り。85%の確度でコミットできる完了日はいつか。先にリスクを潰すべきタスクはどれか」

Claudeが`identify_schedule_risk`を呼び出し、タスクネットワークに対してシード固定のモンテカルロシミュレーションを実行し、P85の完了日とタスクごとのクリティカルパス頻度で答えます。そのままステアリング会議に持ち込める数字です。

これが実務での型です。単一タスクにはPERT、タスクの繋がり全体にはモンテカルロ。

## マーケットプレイス掲載は後日

MCPマーケットプレイスへの掲載をロードマップに載せています。実現すればワンクリックで導入できるようになります。それまではPyPIが正規の入手経路です。必要なのは`uvx pmorun-mcp`だけです。

## さらに詳しく

[GitHub上のサーバーREADME](https://github.com/lemur47/logic/blob/main/mcp_server/README.md)に、各ツールの実例、構造化エラーの仕様、アーキテクチャ、ソースからの実行方法をまとめています。パッケージは[logicリポジトリ](https://github.com/lemur47/logic)の他の部分と同じくMITライセンスです。
