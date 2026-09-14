# RDL Reference Sources

## 目的

RDL Enterpriseの設計・実装・レビューで参照する外部リポジトリの優先順位と使い分けを固定します。これは外部リポジトリの内容を無条件に取り込む指示ではなく、変更の意味境界を確認するための参照規約です。

## 最上位参照

### RDL_Core

- URL: https://github.com/Aporapeiron/RDL_Core
- 現行意味基準: **T0 BASE / SPEC v2.3**
- 主な層: T0 / T1 / TD
- 参照対象: BASE、SPEC、SILN操作、共有語彙、展開・検査・選別・再構成
- 用途: RDLの意味境界、最低動作、形成・代謝工程の確認

RDL_CoreのT0/T1/TDと、そこに規定されたT2・各系との責務分担を、Enterprise側の実装解釈より上位の意味参照とします。T2の具体的な道具は、RDL_FunctionsやRDL_Durability_Modulesなどの対応リポジトリを参照します。

Enterpriseに残る `EFP`、observable `xi`、`Function = Compiled M_B` 等の旧実装語は、現行Coreより上位の意味根拠にはしません。互換コードとして残る期間があっても、Core v2.3へ翻訳して解釈します。

## 現行Core v2.3の最小翻訳規律

```text
SILN
  ↕ {RIB_i}
Purpose / B
  ↓
M_B + RIB_B
  ↓
F = interp(M_B, RIB_B)
```

Enterpriseでは少なくとも次を固定します。

```text
raw request / provider response / feedback != RIB_B
RIB_B != F
Function != M_B
noise / uncertainty / coverage != ξ
static structural conflict != E != H
Human Attention != H
```

`F / F'` をCore比較として使う場合は、同じpre-update `M_B` と意味に影響する凍結条件を使い、`E = Δ(F, F')` とします。

## 組織内の補助参照

組織全体のリポジトリ一覧は https://github.com/Aporapeiron を入口とします。各リポジトリは、変更の役割に応じて必要な場合だけ参照します。

| 変更の役割 | 主な参照先 | 確認する内容 |
|---|---|---|
| 基盤・語彙・SILN工程 | RDL_Core | BASE / SPEC v2.3 / T1 / TDとの整合 |
| 再利用Function・比較・翻訳 | RDL_Functions | Functionの型付きI/O、Boundary、Provenance、`Function != M_B` |
| 耐久・破断・Replay・Perturbation | RDL_Durability_Modules | T1工程を支援する検査道具、RIB/RIB_Bと対象SILNの境界 |
| Human / Game / Music等の適用 | 対応する各リポジトリ | Probe、Selection、許容損失、用途固有Policy |
| Enterprise実装 | RDL_Enterprise | Core契約の実装、Adapter、E2E、運用Lifecycle |

## 参照順

```text
変更の意味を確認
  ↓
RDL_Core BASE / SPEC v2.3 + T1 / TD
  ↓
RDL_Enterprise の Route / Coding Principles / v2.3 Migration Audit
  ↓
必要な場合だけ Functions / Durability / 用途別リポジトリ
  ↓
Boundary / Provenance / Policyを確認して実装
```

## 参照時の注意

- 外部リポジトリの実装や文書を、EnterpriseのCore契約へ自動昇格しない。
- Repositoryの所属と理論層は一対一とは限らない。
- T0 / T1の工程、T2の道具、用途固有Policyを混同しない。
- 参照先の変更も有限境界内の措定であり、必要に応じて再確認する。
- 新しい型を追加する前に、実際の代表Scenarioの破断を再検査できないか確認する。
- 旧語をrenameするだけで移行完了としない。型・入力取得・H・Function lifecycle等の役割が現行Coreと一致するか検査する。

## 短縮ルール

> **意味はRDL_Core v2.3で確認し、実装はRDL_Enterpriseで検証し、道具と用途差は該当リポジトリで補う。**
