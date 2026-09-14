# RDL Enterprise - 関係力学に基づく業務AI Runtime / Reference Implementation

RDL Enterpriseは、RDLの意味境界を業務AI Runtimeとして検証する参照実装です。LLMをAIの本体とせず、判断、観測、権限、外界作用、証跡を分離して扱います。

このリポジトリはRDLの完全実装や、世界の真理を決定するシステムを宣言しません。すべての一致、再現、十分性、安全性は、明示された有限Boundaryにおける性質です。

現在の意味基準は **`Aporapeiron/RDL_Core` T0 BASE / SPEC v2.3** です。旧 `EFP`、`CompiledMB`、`xi_obs` 等は移行期間の互換名として残る場合がありますが、現行Coreの規範語彙ではありません。

## Project Status — Core v2.3 staged migration

現在のmigration surfaceでは、**P1–P9までを現在の有限テストBoundaryで実装済み**です。残る主要ゲートはP10のreal interaction acceptanceです。

```text
raw request / later observation
        ↓ acquisition under Purpose / B
      RIB_B(t) / RIB_B(t+Δ)
        ↓ same pre-update M_B
       F / F'
        ↓
   E = Δ(F, F')
        ↓ unresolved only
        H
```

現在までに明示化した主な境界は次です。

```text
raw BusinessInput / FeedbackResult != RIB_B
RIB_B                              != F
static structural conflict         != E != H
acquisition / coverage gap         != E != H
coverage metric                    != ξ
Human Attention                    != H
Function                           != M_B
```

`EnterpriseRuntimeRIBBridge` では、requestと後続observationsをそれぞれ `RIBSection` として取得し、same pre-update `M_B` / frozen interpretation contextで `F / F'` を形成します。canonical `Δ(F,F')` の未解決成分だけをoperational Hへ残し、旧 `e_input` はdiagnosticとして観測可能でもH / M_Δを直接駆動しません。

Canonical `F / F'` formationは `RIBSection.to_business_input()` に依存しません。request / subsequent `RIBSection`、canonical mismatch、unresolved-mismatch state、coverage state、operational H adapter stateは、現在のsingle-writer SQLite Boundaryでrestartを跨いで保持されます。

Function側では、正規名称として次を公開しています。

```text
CompiledFunction
ActiveFunction
ConditionalCompiledFunction
ConditionalFunctionPromotionRecord
ConditionalFunctionActivationRecord
```

旧 `CompiledMB` / `ConditionalCompiledMB` / `ActiveCompiledMB` 等は互換面として残します。型名が残ることは `Function = M_B` を意味しません。

次の必須境界は **P10 — real interaction acceptance** です。read-only Jiraのreal-provider observationからcanonical `RIBSection → F → later RIBSection → F' → E` までを確認するlive testはありますが、**actual response/actionによって外部条件が変わり、その後のreal RIB_Bで差が観測される完全chain**はまだ未完了です。

この進捗は完成宣言ではありません。

```text
current finite test Boundaryで migration contract成立
!= terminally complete
!= universally valid
!= real-world interaction fully evaluated
```

## Concept

RDL Enterpriseが目指すのは、常に正しい知識を持つAIではありません。

実務では、情報は欠け、規則は古くなり、担当や権限は変わり、昨日まで有効だった判断も破れます。RDLは、そのような変化や破断を例外として排除するのではなく、**有限な観測の中で判断し、壊れた箇所を見つけ、必要な範囲だけ更新しながら仕事を続ける**ための構造を扱います。

```text
観測する
  -> 現在使える構造で判断する
  -> 破断・不足・矛盾が現れる
  -> 必要な範囲だけ人間や外部系へ戻る
  -> 検証された変更だけを定着させる
  -> 再び仕事を続ける
```

「一度成功した」「LLMがそう答えた」「権限者がそう言った」という事実を、そのままTruthへ昇格させません。Observation、Candidate、Commitment、Active、Authority、履歴を分離し、現在の有限Boundaryで何が使えるかを管理します。

## Core v2.3 interaction model

Enterpriseでは、raw eventをそのままCore `RIB_B` とみなしません。

```text
nonlinear relational network
        │
       SILN
      ↕ ↕ ↕
   RIB₁ RIB₂ RIB₃ ...
        │
        ↓ Purpose / B
   M_B + RIB_B
        ↓
F = interp(M_B, RIB_B)
```

時間比較が必要な場合は、同じpre-update `M_B` と意味に影響する凍結条件を使います。

```text
RIB_B(t)     = Section_B({RIB_i(t)})
F(t)         = interp(M_B, RIB_B(t))

RIB_B(t+Δ)   = Section_B({RIB_i(t+Δ)})
F'(t+Δ)      = interp(M_B, RIB_B(t+Δ))

E(t+Δ)       = Δ(F, F')
```

`ξ` は有限Bで未回収となる関係であり、noise、missing rate、unknown count、coverage score、queue load等のobservable runtime quantityではありません。

## 現在動いている製品経路

現在の製品入口は、自然文からのread-only Jira/JSM照会です。

```text
自然文 -> routing -> Tool Candidate -> Bearer / Authority check
      -> Jira REST observation -> bounded result -> ActionLedger
      -> SQLite persistence -> process restart recovery
```

例えば、`IT-3って今どうなってる？`を受けると、対象issueを推測で補わず、`atlassian.jira.issue.lookup`のread-only Candidateを生成してから既存のAuthorityとTool boundaryを通してJiraを観測します。曖昧な`VPNの件どうなった？`は`UNRESOLVED`のまま実行しません。

実証済みの製品経路には、自然文routing、Authority/domain scope検査、Jira応答の`case_id`・`summary`・`status`・`owner`へのbounded projection、`assignee=null`の`owner=None`保持、ActionLedger、SQLite永続化、別Pythonプロセスでの再起動復元があります。

Interaction Reflection側では、static structural conflictはそれ自体を`E`や`H`へ昇格させません。後続interactionから別の `RIB_B(t+Δ)` が形成され、same pre-update `M_B`による `F'` と `Δ(F,F')` が成立した場合にのみCore mismatch候補になります。Human Attentionはsystem Hとは別のEnterprise-local review機構です。

## Operational Boundary

```text
localhost (127.0.0.1)
  + static Bearer service entry
  + single service principal
  + single Runtime / single-writer SQLite
  + read-only Jira provider
  + durable ActionLedger
```

外部credentialは環境変数から読み込み、内部結果、Ledger、SQLiteへ保存しません。Jiraの外部応答はそのまま内部状態へ流さず、必要な有限項目へ投影します。

## 守っている意味境界

```text
credential verified       != human identity proven
Observation               != Tool Candidate != Commitment != Active
persisted Observation     != current Observation
ActionLedger              != Truth
Authority                 != Truth
UNKNOWN                   != UNRESOLVED != NOT_EVALUATED
Similarity                != Rupture
Structural Conflict       != E != H
Human Attention load      != H
Function                   != M_B
RIB_B                      != F
coverage gap               != ξ
```

Candidate生成は実行を意味しません。read-only queryは明示的なreplay指定がない限り毎回providerを再観測します。provider observationやLedgerは有限な証跡であり、無条件の真実として扱いません。

## Function lifecycle

構造と演算成果物を分離します。

```text
M_B
= SILNをBのもとで扱う有限な自己側・解釈構造断面

Function
= finite contractを持つ再利用可能なoperator
```

現行canonical lifecycleは次です。

```text
StructureCandidate
→ FunctionCandidate
→ CompilationRecord(PASSED)
→ CompiledFunction
→ PromotionDecision
→ ActiveFunction
→ Deactivation / Recompilation / Supersession
```

conditional lineageも `ConditionalCompiledFunction` から正規のPromotion / Activation経路を通せます。旧 `*CompiledMB` 名称群は後方互換のため残します。

## 知識沈澱とコスト軽量化

Tier 3で解けたことだけで、知識が自動的に`M_B`へ沈澱するわけではありません。

```text
検証された知識候補 -> 所定の更新経路 -> M_B / cacheへ定着
                                      -> 再利用可能なら後続コスト低下
```

反復構造、検証・教育、再利用回数によって低コスト経路へ移行し得ます。未学習パターンや人間確認が必要な案件が常に低コスト化することは主張しません。

## Deterministic Simulation Boundary

Simulation / replayで意味遷移に使う観測時刻は外生条件です。明示された `BusinessInput.created_at` は `FrozenInterpretationContext.constraint_evaluation_time` へ固定され、constraint freshnessが実wall clockへ暗黙依存しないようにします。

現在の全テストでは、60日long-term lifecycleを含む条件固定replayがこの境界で通っています。これは指定されたSimulation条件での再現性であり、世界全体の決定論を意味しません。

## Restart Durability Boundary

現在のP9受入では、次の有限状態がsingle-writer SQLiteを介してrestartを跨ぎます。

```text
request RIBSection
subsequent RIBSection
F / F' lineage in CaseSnapshot
canonical mismatch observation
v23 unresolved-mismatch state
v23 coverage state
v23 operational H adapter state
```

timeoutでは、後続sectionが無い場合に `F' / E / H` を捏造せず、coverageだけを保持したままrestartできます。

これは現在のSQLite Runtime Boundary内でのdurabilityであり、multi-process、distributed、tamper-proof durabilityを意味しません。

## Benchmark

`benchmark_cost_curve.py`による合成ワークロードの観測値です。実API課金額ではなく、Tierごとのtoken-equivalentモデルです。

```text
Synthetic workload: 60 tickets
Pure LLM        108,000 token-equivalent
Standard RAG     60,000 token-equivalent
RDL Enterprise   46,800 token-equivalent
vs Pure LLM      -56.7%
vs Standard RAG  -22.0%
```

この削減率はtraffic mix、seed coverage、反復率、人間による知識供給に依存します。これは再現条件付きの観測値であり、一般的な性能保証ではありません。

## Live Acceptance

```text
Windows + separate Python process + Bearer authentication
  + real Atlassian Jira + bounded read-only lookup
  + null owner preservation + SQLite + process restart
  + credential string not detected in tested DB
```

これは現在のcredential、database、provider、localhost構成に対する有限な受入です。完全なsecret非漏洩や外部環境全般の安全性を証明するものではありません。

P10 live testは現在、real Jira observationを `EnterpriseRuntimeRIBBridge` へ入れ、request `RIBSection → F → later RIBSection → F' → canonical E/H` を確認する契約になっています。ただしread-onlyの連続観測ではissueが変化しない場合もあり、その場合 `E = 0` は正当です。

したがって、**real structural conflict / actionable condition → actual response/action → changed interaction conditions → later real RIB_B → F/F' → E** の完全な実運用chainはまだP10の未完了境界です。

## これは確立していないこと

- internet-facing security、人間identityそのものの証明
- multi-process / distributed durability、tamper-proof audit
- universal secret non-leakage、Jira以外のprovider互換性
- RDLの完全性や普遍的な真理性
- 不可逆Toolのdurable Approval
- real structural conflictからresponse、later `RIB_B`、`F/F'`、`E/H`までの完全な実運用縦断

## Quick Start

### Read-only Jira API

credentialをファイルへ書かず環境変数から渡します。

```powershell
$env:RDL_API_BEARER_TOKEN = "<local-api-token>"
$env:RDL_API_STORE_PATH = "D:\GitHub\RDL_Enterprise\data\rdl_api.sqlite3"
$env:RDL_ATLASSIAN_BASE_URL = "https://<your-domain>.atlassian.net"
$env:RDL_ATLASSIAN_EMAIL = "<service-email>"
$env:RDL_ATLASSIAN_TOKEN = "<api-token>"
python .\rdl_api.py
```

```powershell
$body = @{ text = "IT-3って今どうなってる？" } | ConvertTo-Json -Compress
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
Invoke-WebRequest -UseBasicParsing -Method Post `
  -Uri "http://127.0.0.1:8765/query" `
  -Headers @{ Authorization = "Bearer <local-api-token>" } `
  -ContentType "application/json; charset=utf-8" -Body $bytes
```

### CLI

```powershell
python .\rdl_query.py "IT-3って今どうなってる？" --actor-id local-operator
python .\rdl_query.py "IT-3って今どうなってる？" --actor-id local-operator --json
```

### Simulation and tests

```powershell
python .\run_simulation.py
python .\run_multiagent_sim.py --scenario lifecycle --days 60
python .\benchmark_cost_curve.py
python -m pytest -q
```

### Manual sedimentation benchmark

合成マニュアルと合成案件だけを使い、教育深度、再利用、例外停止、修復後回帰を比較する構造特性ベンチマークです。実務価値や普遍的な正しさを証明するものではありません。

```powershell
python .\benchmark_manual_sedimentation.py
```

結果は`benchmark_results/manual_sedimentation_latest.json`と`.csv`へ出力されます。D1/D2/D3は同一manual・同一case setの保持深度だけを変え、golden outcomeはRuntimeへ渡しません。

## 現在の主要構成

```text
rdl_api.py                              localhost API起動入口
rdl_query.py                            read-only query CLI
src/rdl_enterprise/http_api.py          HTTP / Bearer / localhost boundary
src/rdl_enterprise/business_query.py    自然文query orchestration
src/rdl_enterprise/tool_routing.py      Tool Candidate生成
src/rdl_enterprise/tool_execution.py    ToolRegistryと実行状態
src/rdl_enterprise/atlassian_jira_provider.py Jira read-only adapter
src/rdl_enterprise/service.py           認証済みservice境界
src/rdl_enterprise/persistence.py       SQLite persistence
src/rdl_enterprise/runtime.py           既存業務Runtime / compatibility lifecycle
src/rdl_enterprise/interaction.py       RIBSection acquisition
src/rdl_enterprise/runtime_rib_bridge.py Core v2.3 RIB / operational H bridge
src/rdl_enterprise/mismatch_state.py    F/F' mismatch・coverage分離
src/rdl_enterprise/operational_h.py     v2.3 operational H adapter
src/rdl_core/compiled_function_types.py canonical CompiledFunction
src/rdl_core/conditional_compiled_function_types.py canonical conditional Function lifecycle
src/rdl_enterprise/attention.py         bounded Human Attention aggregation
src/rdl_enterprise/presentation.py      人間向け結果表示
tests/test_runtime_rib_bridge.py        v2.3 bridge契約
tests/test_runtime_rib_persistence.py   P9 canonical restart durability
tests/test_p10_live_interaction.py      P10 live canonical RIB acceptance
tests/test_compiled_function_migration.py Function migration契約
tests/test_product_acceptance.py        製品受入・永続化・縦断テスト
docs/INTERACTION_REFLECTION_PLAN_v0.3.md current v2.3 migration plan
docs/RDL_Core_v2.3_Migration_Audit.md   migration audit
docs/RDL_Product_Status_v0.1.md         製品Boundaryと残件
```

詳細な実装規律は `docs/RDL_Coding_Principles.md`、Function / M_B分離は `docs/RDL_Compiled_MB.md`、段階計画は `docs/INTERACTION_REFLECTION_PLAN_v0.3.md` を参照してください。

## 次の評価境界

次の設計対象は新しい抽象を増やすことではなく、**P10のreal changed-condition chainを一本観測すること**です。

```text
real condition / conflict
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

この鎖を無理に作るのではなく、Boundary / Provenanceを回収できる実 interaction が得られた時点でP10受入を行います。