# RDL Core Route v0.1

## 位置づけ

本書は、既存のPhase計画とCore Extraction Gateの上位に置く、役割分離と段階的深掘りの運用方針です。現在のCoreを運用十分なv0として扱い、型や状態を無条件に増やさず、代表シナリオで観測された破断に応じて必要な範囲だけ深掘りします。

この方針自体も有限境界Bに基づく運用上の措定であり、再検査・更新対象です。

## 上位原則

1. Similarity CheckとRupture Checkを分離する。
2. Similarity、Rupture、Revision、Promotionを同一判断へ潰さない。
3. 通常運用は、有限なM_Bを参照する局所Function / Operatorによる浅い経路とし、破断・未解決時だけ検査深度を上げる。
4. `Function != M_B`。FunctionはM_Bそのものではなく、有限境界下で局所拘束を適用する再利用可能な演算契約として扱う。
5. Observation、Candidate、Commitment、Active Constraintを分離する。
6. UNKNOWN、UNRESOLVED、NOT_EVALUATEDをFAILUREやNOT_MATCHへ変換しない。
7. CoreはTruth、Reality、Completeness、absolute safetyを認定しない。
8. RDL自身の語彙・計画・境界も自己免除せず再検査可能にする。

## 責務境界

| 役割 | 主な責務 | 境界 |
|---|---|---|
| Core Contracts | Boundary、Provenance、Status、Authorityなどの共通契約 | Truthや終端閉包を認定しない |
| Observation / Runtime | 有限入力と観測結果の記録 | 観測からCommitmentを作らない |
| M_B Structure | SILNの有限な自己側・解釈構造断面を保持する | Functionや実行結果と同一視しない |
| Function / Operator | B_f、input/output contract、局所拘束、Provenanceを持つ有限演算 | M_B、SILN、RIB_Bそのものではない |
| Similarity | 比較、探索、cluster・pattern候補の生成 | RuptureやPromotionを決めない |
| Rupture / Durability | 現行構造またはFunction契約の継続可否を再検査 | Revision内容や即時停止を決めない |
| Evolution / Relearning | 破断証拠からRevision・vNext候補を作る | Candidateを自動Commitしない |
| Compilation | 検証済みFunction Candidateをversioned executable artifactへ固定 | M_Bそのものへの同一化、Active化を行わない |
| Lifecycle | Promotion、Activation、Deactivation、Supersession | Truthへ昇格しない |
| Integration | 各役割を有限順序で接続する | 個別責務を一枚岩へ戻さない |

## 深度モデル

```text
L0  通常運用: finite M_B + lightweight Function / Operator
L1  Rupture Gate: mismatch・未解決の再検査
L2  Local Inspection: condition・exception・provenance
L3  Relational Inspection: Similarity・history・structure
L4  Adaptive Escalation: LLM・search・humanをCandidate材料として利用
L5  Recompile: validation・function compilation・promotionを経て浅い経路へ戻る
```

深い検査へ進んだこと自体を成功とはしません。原因を現在の境界で再構成できた時点で、浅い経路へ戻します。

## FunctionとM_Bの接続

現行の移行規約は次です。

```text
SILN
  ↓ B
M_B + RIB_B
  ↓
F = interp(M_B, RIB_B)

Function_B
  = Operator(B_f, input contract, local constraints,
             transform/evaluate rule, output contract,
             provenance, unresolved)
```

Function内部の局所拘束が、ある用途ではM_Bの局所実装断面として統合されることはあります。しかし、そこから `Function = M_B` は導きません。旧 `CompiledMB` / `ActiveCompiledMB` 等の型名は互換移行対象であり、現行の意味規範ではありません。

## 新規型の追加条件

次のいずれかを満たす場合に限り、Coreへの新しい型・状態・Gateを追加します。

- BASE / SPEC違反を直接防ぐ。
- 代表シナリオの実際の破断を、既存型では再検査できない。
- Boundary、Provenance、evidence、lineageの回収に不足がある。
- 複数用途で繰り返し現れ、共通契約として抽出できる。

判断文は次の一つに固定します。

> この型がないと、今起きている破断を再検査できないか。

## 次の実行ゲート

次の優先順位は、追加抽象を先に増やすのではなく、代表シナリオを現在のCoreで通すことです。

1. 条件付き業務判断: Runtime → NOT_MATCH / UNRESOLVED → Rupture → Revision → vNext。
2. 類似事例を伴う破断: Rupture evidence → Similarity → 構造候補。
3. UNKNOWNを含む運用: 未取得証拠 → UNRESOLVED → 追加観測・検索・Human。
4. Function移行: 旧 `CompiledMB` 名称群を互換層へ閉じ込め、Function contractとM_B structureを別型として維持する。

各シナリオで具体的な破断点が出た場合だけ、該当する役割の型・関数・Adapterを追加します。

## 旧Phaseとの関係

旧Phase 0–18は履歴と詳細チェックリストとして保持します。今後の優先順位は本書の役割別判断を上位に置き、旧Phaseは実装順の候補として扱います。
