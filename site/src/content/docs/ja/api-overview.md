---
title: "ロジックAPI"
description: "オープンソースの意思決定モジュール — セルフホストまたはPythonで利用可能。ホスティングAPIは近日公開。"
order: 1
---

## ロジックAPIとは

logicリポジトリは、純粋なPython関数とFastAPIエンドポイントとして構成可能な意思決定モジュールを提供します。すべてのモジュールはオープンソース、デフォルトでステートレス、そしてあなた自身のシステムにインポートできるように設計されています。

## 利用可能なモジュール

### TCO（総所有コスト）— 公開中

| 関数 | 説明 |
|------|------|
| `calculate_tco()` | NPV調整付きの総コストと年間コストを計算 |
| `compare_options()` | 年間コストで複数の選択肢をランク付け |
| `breakeven_analysis()` | 高い初期コストがいつ回収されるかを分析 |

### 近日公開

| モジュール | カテゴリ | 説明 |
|-----------|---------|------|
| PERT | 見積もり | 三点見積もり（楽観 / 最頻 / 悲観） |
| Base-rate | 予測 | 主観的バイアスを減らす参照クラス予測 |
| NPV | 財務 | 正味現在価値分析 |

## セルフホスト（今すぐ利用可能）

リポジトリをクローンしてローカルで実行：

```bash
git clone https://github.com/lemur47/logic.git && cd logic
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload
```

APIは `http://127.0.0.1:8000` で利用可能。エンドポイントの詳細は `/docs`（Swagger UI）で確認できます。

### エンドポイント（セルフホスト）

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/tco/calculate` | ステートレスTCO計算 |
| `POST` | `/tco/compare` | 年間コストで選択肢を比較 |
| `POST` | `/tco/breakeven` | 2つの選択肢の損益分岐点分析 |
| `POST` | `/tco/scenarios` | シナリオの保存 |
| `GET` | `/tco/scenarios` | シナリオ一覧（ページネーション、検索対応） |
| `GET` | `/tco/scenarios/stats` | 統計情報 |
| `GET` | `/health` | ヘルスチェック |

### Pythonインポート

APIを使わずにロジックを直接利用することもできます：

```python
from app.tco.core import calculate_tco

result = calculate_tco(
    initial_price=450000,
    useful_life_years=12,
    residual_value=90000,
    annual_maintenance=5000,
)
print(f"年間コスト: {result['annual_cost']:,.0f}")
```

## ホスティングAPI

`api.pmo.run` でのホスティングAPIはフェーズ2で提供予定です。認証、レート制限、暗号化ストレージ付きのシナリオ保存機能を含みます。

現時点ではセルフホストが最良の選択肢です — そしてそれは永久に無料です。

## ソースコード

[github.com/lemur47/logic](https://github.com/lemur47/logic) — MITライセンス
