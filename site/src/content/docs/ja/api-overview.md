---
title: "API概要"
description: "PMOロジックAPIの使い方 — エンドポイント、認証、使用例。"
order: 1
---

## ベースURL

```
https://api.pmo.run
```

## 利用可能なエンドポイント

### TCO（総所有コスト）

| メソッド | パス | 説明 |
|----------|------|------|
| `POST` | `/tco/calculate` | ステートレスTCO計算 |
| `POST` | `/tco/scenarios` | シナリオの作成 |
| `GET` | `/tco/scenarios` | シナリオ一覧 |
| `GET` | `/tco/scenarios/{id}` | IDでシナリオ取得 |
| `PUT` | `/tco/scenarios/{id}` | シナリオの更新 |
| `DELETE` | `/tco/scenarios/{id}` | シナリオの削除 |

### ヘルスチェック

| メソッド | パス | 説明 |
|----------|------|------|
| `GET` | `/health` | ヘルスチェック |

## リクエスト形式

すべてのエンドポイントはJSONを受け付け、JSONを返します。リクエストに`Content-Type: application/json`を含めてください。

## 使用例

```bash
curl -X POST https://api.pmo.run/tco/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "options": [
      {
        "name": "選択肢A",
        "initial_cost": 200,
        "annual_costs": [{ "name": "トナー", "amount": 180 }],
        "years": 5
      }
    ]
  }'
```

他のモジュール（NPV、IRR、PERT）は近日公開予定です。
