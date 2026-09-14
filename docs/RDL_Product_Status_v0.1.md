# RDL Enterprise Product Status v0.1

この文書は、RDL Enterpriseを業務AIとして運用するための現在の有限Boundaryを記録します。完了判定は、すべての環境・業務・外部サービスに対する完全性を意味しません。

意味基準は `Aporapeiron/RDL_Core` T0 BASE / SPEC v2.3 です。

## Current Boundary

現在のv0業務AIランタイムは、単一Runtimeとsingle-writer SQLite永続化を前提にします。

製品ライフサイクルの既存経路は次です。

```text
authenticated actor
  -> EnterpriseService
  -> Runtime / Tool Candidate
  -> authorized connector / tool
  -> ActionLedger
  -> feedback
  -> atomic persistence and bounded learning
```

Core v2.3 migration surfaceではinteraction側を次のように分離しています。

```text
raw business request / later observation
  -> acquisition under Purpose / B
  -> RIBSection  (Enterprise representation of RIB_B)
  -> same pre-update M_B interpretation
  -> F / F'
  -> E = Δ(F,F')
  -> unresolved component only
  -> operational H
```

`EnterpriseRuntimeRIBBridge` は request / later `RIBSection` をcanonical interpretation inputとして直接扱います。`RIBSection.to_business_input()` はhistorical compatibility surfaceとして残りますが、canonical `F / F'` formationの依存ではありません。

## Completed Product / Migration Layers

- **Persistence / Restart Recovery**: pending/resolved case、M_B、legacy compatibility state、Level0 cache、経験履歴、再編proposal、canary deployment、ActionLedgerを再起動後に復元します。
- **AuthN / AuthZ**: authenticated `AuthorityContext`、domain scope、feedbackのticket identity、actor provenanceを検査・記録します。
- **Tool Execution**: effectful toolのoperation identity、payload binding、durable `PLANNED`、成功・失敗・未実行・不確定、provider reconciliation、retry safetyを扱います。
- **Workflow vertical slice**: read-only Jira/JSM lookupを認証済み業務入力とToolRegistryへ接続しています。
- **RIB acquisition P1/P2**: requestとlater observationを別々の `RIBSection` として取得します。
- **F/F' comparison P3**: same pre-update `M_B` / frozen interpretation contextを維持します。
- **H separation P4/P5**: RIB bridgeのoperational Hはunresolved canonical `Δ(F,F')`だけを受け、`e_input` / coverageは直接HやM_Δを駆動しません。
- **ξ separation P6**: observable quantityは`coverage_gap_score`として扱い、`xi_obs`はdeprecated compatibility aliasのみです。
- **Function migration P7**: `CompiledFunction`、`ActiveFunction`、`ConditionalCompiledFunction`およびcanonical conditional lifecycleをpublic Core APIとして提供します。旧`*CompiledMB`名は互換面です。
- **Native RIB interpretation P8**: initial `F` とcanonical `F'` は `RIBSection` を直接解釈します。canonical pathはBusinessInput projectionを要求しません。
- **Canonical restart durability P9**: request/subsequent `RIBSection`、canonical mismatch、unresolved-mismatch state、coverage state、operational H adapter stateをcurrent SQLite Runtime Boundaryでrestart後に復元します。timeout coverageも`F' / E / H`を捏造せず保持できます。

P9 acceptance run `f102917c5bf1ddaaca2d58d65667bdb5ddbfa8f8` では `314 passed, 4 skipped, 6 subtests passed` でした。

## Explicit Limits

- real structural conflict / actionable conditionからactual response、changed interaction conditions、later real `RIB_B`、`F/F'`、`E`までを一続きに観測するP10 real interaction acceptanceは未完了です。
- current live Jira testはread-only real-provider observationsをcanonical `RIBSection → F → later RIBSection → F' → E`へ通しますが、外部状態変化そのものは自動生成しません。
- tool selectionとpayload構成には既存の明示的routing/contractが残ります。未解決入力を推測で実行しません。
- `IRREVERSIBLE` toolのdurable ApprovalRecordは現在の製品Boundary外です。
- AuthenticationContextは上流で認証済みという前提の内部service境界です。人間identityそのものを証明しません。
- SQLiteは単一Runtime / single-writer Boundaryです。multi-worker競合や分散耐久性は未閉鎖です。
- current restart durabilityはtamper-proof auditを意味しません。
- 現在のテスト成功は、指定された有限Boundaryで契約違反が観測されなかったことを示すだけです。

## Current Semantic Separations

```text
raw input              != RIB_B
RIB_B                  != F
Function               != M_B
coverage gap           != ξ
coverage / e_input     != Core H
Structural Conflict    != E != H
Human Attention        != H
Observation            != Candidate != Commitment != Active
Authority              != Truth
UNKNOWN                != UNRESOLVED != NOT_EVALUATED
```

## Acceptance Direction

P1–P9の内部migrationは現在の有限Boundaryで閉じています。次の製品作業は新しいCore型を増やすことではなく、P10のreal changed-condition chainを一本観測することです。

```text
real structural conflict / actionable condition
  ↓
actual response / action
  ↓
changed external interaction conditions
  ↓
later real RIB_B
  ↓ same frozen pre-update M_B
F'
  ↓
E = Δ(F,F')
  ↓ unresolved when applicable
H
```

P10では、Boundary / Provenanceを回収できる実 interaction を対象にし、外部状態変化をテスト都合で捏造しません。

実際に破断や情報不足が現れた境界だけを次の設計対象にし、追加抽象を先行させません。
