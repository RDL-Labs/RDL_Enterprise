# RDL Enterprise Product Status v0.1

この文書は、RDL Enterpriseを業務AIとして運用するための現在の有限Boundaryを記録します。完了判定は、すべての環境・業務・外部サービスに対する完全性を意味しません。

意味基準は `Aporapeiron/RDL_Core` T0 BASE / SPEC v2.3 です。

## Current Boundary

現在のv0業務AIランタイムは、単一RuntimeとSQLite永続化を前提にします。

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

Core v2.3 migration surfaceでは、interaction側をさらに次のように分離しています。

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

`EnterpriseRuntimeRIBBridge` は現在このv2.3意味経路を既存Runtime lifecycleへ接続します。RIBSectionはまだcompatibility projectionを通して既存BusinessInput/Cascadeへ渡されるため、native Runtime cutoverは未完了です。

## Completed Product / Migration Layers

- **Persistence / Restart Recovery**: pending/resolved case、M_B、legacy HState、Level0 cache、経験履歴、再編proposal、canary deployment、ActionLedgerを再起動後に復元します。
- **AuthN / AuthZ**: authenticated `AuthorityContext`、domain scope、feedbackのticket identity、actor provenanceを検査・記録します。
- **Tool Execution**: effectful toolのoperation identity、payload binding、durable `PLANNED`、成功・失敗・未実行・不確定、provider reconciliation、retry safetyを扱います。
- **Workflow vertical slice**: read-only Jira/JSM lookupを認証済み業務入力とToolRegistryへ接続しています。
- **RIB acquisition P1/P2**: requestとlater observationを別々の `RIBSection` として取得します。
- **F/F' comparison P3**: same pre-update `M_B` / frozen interpretation contextを維持します。
- **H separation P4/P5**: RIB bridgeのoperational Hはunresolved canonical `Δ(F,F')`だけを受け、`e_input` / coverageは直接HやM_Δを駆動しません。
- **ξ separation P6**: observable quantityは`coverage_gap_score`として扱い、`xi_obs`はdeprecated compatibility aliasのみです。
- **Function migration P7**: `CompiledFunction`、`ActiveFunction`、`ConditionalCompiledFunction`およびcanonical conditional lifecycleをpublic Core APIとして提供します。旧`*CompiledMB`名は互換面です。

## Explicit Limits

- RIBSectionはまだ既存Runtime/Cascadeへcompatibility projectionされます。P8ではこれをnative Runtime boundaryへ移します。
- canonical RIBSection / mismatch stateの第一級restart persistenceはP9で未完了です。
- real structural conflictからactual response、changed interaction conditions、later real RIB_B、F/F'、Eまでを一続きに観測するP10 real interaction acceptanceは未完了です。
- tool selectionとpayload構成には既存の明示的routing/contractが残ります。未解決入力を推測で実行しません。
- `IRREVERSIBLE` toolのdurable ApprovalRecordは現在の製品Boundary外です。
- AuthenticationContextは上流で認証済みという前提の内部service境界です。人間identityそのものを証明しません。
- SQLiteは単一Runtime / single-writer Boundaryです。multi-worker競合や分散耐久性は未閉鎖です。
- 現在のテスト成功は、指定された有限Boundaryで契約違反が観測されなかったことを示すだけです。

## Current Semantic Separations

```text
raw input              != RIB_B
RIB_B                  != F
Function               != M_B
coverage gap           != ξ
coverage / e_input     != Core H
Structural Conflict   != E != H
Human Attention        != H
Observation            != Candidate != Commitment != Active
Authority              != Truth
UNKNOWN                != UNRESOLVED != NOT_EVALUATED
```

## Acceptance Direction

次の製品作業は新しいCore型を増やすことではなく、現在のcompatibility境界を一段ずつ外すことです。

```text
P8  RIBSection native Runtime cutover
      ↓
P9  canonical RIB / mismatch persistence + restart durability
      ↓
P10 one complete real interaction acceptance chain
```

P8では、既存のAuthority、ActionLedger、Canary、staged commitment、Persistence、frozen `M_B`、Provenance、observation-time determinismを壊さないことを受入条件とします。

実際に破断や情報不足が現れた境界だけを次の設計対象にし、追加抽象を先行させません。
