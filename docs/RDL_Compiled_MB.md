# RDL Compiled Function
## Legacy `Compiled M_B` Compatibility Note

## 位置づけ

本文書は、Enterpriseに残る `CompiledMB` / `ConditionalCompiledMB` 等の旧名称を、現行 `RDL_Functions` と Core v2.3 の役割分離に合わせて読み替える。

旧文書では、

```text
Function = Compiled M_B
```

としていたが、**これは現行定義では採用しない。**

現在は、

```text
Function != M_B
Function != SILN
Function != RIB_B
```

とする。

Functionは、有限なPurpose / Boundaryのもとで、型付き入力を受け、局所拘束・変換・評価規則を適用し、型付き出力とProvenance / unresolved / failure conditionを返す**再利用可能な演算モジュール**である。

特定のRuntimeでFunction内部の拘束や成果物が `M_B` の局所実装断面へ組み込まれることはありうる。しかし、組み込まれることと、Functionそのものが `M_B` であることは同じではない。

---

## 1. 現行Function契約

概念的には次の形を採用する。

```text
Function_B = Operator(
  Purpose / B_f,
  input contract,
  local constraints,
  transform / evaluate rule,
  output contract,
  provenance,
  unresolved / failure conditions
)
```

Enterpriseの現行型では、少なくとも次がこの契約の一部を実装している。

```text
FunctionDescription
  = Function identity / version

FunctionInvocation
  = FunctionDescription
    + BoundaryContext
    + Purpose
    + config
    + Provenance

FunctionCandidate
  = bounded structure-derived candidate

CompilationRecord
  = finite validation observation
```

これらは `M_B` の同義語ではない。

---

## 2. `CompiledMB` という型名の身分

現在のコードには、後方互換上、次の型名が残る。

```text
CompiledMB
ConditionalCompiledMB
ActiveCompiledMB
```

移行期間中、これらは**legacy compatibility names**として扱う。

意味上は、たとえば `CompiledMB` を、

```text
Validated Compiled Function Artifact
```

として読む。

つまり、

```text
CompiledMB.class-name
    != Core上の「M_Bそのもの」
```

である。

将来的には、互換性を維持しながら、

```text
CompiledFunction
ConditionalCompiledFunction
ActiveFunction
```

等の正規名称へ移行する。

旧名称は、新規設計の根拠として使わない。

---

## 3. 構造側とFunction側を分ける

現行Coreで `M_B` は、SILNをある `B` のもとで自己側・解釈側として保持する有限構造断面である。

一方Functionは、その断面や `RIB_B`、`F`、state、profile、record、他Function出力などを、契約に応じて受け取れる演算単位である。

```text
SILN
 ↓ B
M_B                    RIB_B
 │                       │
 └──────┐         ┌──────┘
        ↓         ↓
        Function / evaluator
              ↓
        bounded output
```

これは模式図であり、すべてのFunctionが必ず `M_B + RIB_B` を同時入力に取るという意味ではない。

Functionの入力役割は契約で明示する。

```text
input_role = RIB_B
input_role = F
input_role = state
input_role = profile
input_role = record
input_role = other Function output
```

役割の異なる型を暗黙に接続しない。

---

## 4. 現行コンパイル経路

Enterpriseにおける候補生成・検証・有効化の分離は維持する。

```text
finite observations / relation profiles
        ↓
structure candidate
        ↓
Function Candidate
        ↓ validation / rupture / durability
Compiled Function Artifact
        ↓ promotion
Promoted Function Artifact
        ↓ explicit activation
Active Function
```

各段階は、

```text
Candidate != Validated != Promoted != Active
```

である。

コンパイル済みであることはTruth、Authority、Commitment、世界全体への妥当性を意味しない。

---

## 5. M_B側の更新経路

`M_B` の更新・再構成はFunction lifecycleと同一ではない。

通常の構造変化は、

```text
M_B(t) → M_B(t+Δ)
```

として扱える。

既存構造を再構成する場合は、必要に応じて、

```text
H >= θ
  ↓
M_Δ
  ↓ inspection / selection / reconstruction
M_B'
```

へ進む。

Functionの再コンパイルが起きたから自動的に `M_B → M_B'` が成立するわけではない。逆に、`M_B` の再構成が起きても、すべてのFunctionを必ず再コンパイルするとは限らない。

両者の接続はRuntime / application Boundaryで明示する。

---

## 6. Provenanceと有限性

Function applicationは、少なくとも、

```text
Function identity/version
Purpose / Boundary
input role
config
Provenance
output role
unresolved / failure state
```

を必要に応じて回収可能にする。

Function outputは世界そのものではなく、有限な契約・境界のもとで形成された出力である。

したがって、

```text
Function success != universal truth
Function validation != terminal completeness
Function activation != world identity
```

である。

---

## 7. 時間スケール

旧文書では、

```text
Working M_B
Adaptive M_B
Persistent M_B
Compiled M_B
```

を一つの時間スケール列として並べていた。

現行では `Compiled M_B` をその列から外す。

構造側の運用分類として、必要なら、

```text
Working M_B    : 現在案件・会話・局所状態に強く依存する有限構造断面
Adaptive M_B   : 経験や再検査を受けて変化中の有限構造断面
Persistent M_B : 長期に再利用される構造候補・保持構造
```

を置ける。

一方、

```text
Compiled Function
```

は**演算成果物のlifecycle分類**であり、M_Bの時間スケール分類ではない。

---

## 8. Enterprise移行規律

移行中は既存コードを一度に破壊しない。

```text
old public type/name
    ↓ compatibility alias / adapter
canonical Function role
```

の順で移す。

新規コードでは、次を避ける。

```text
Function = M_B
Function = SILN
Function = RIB_B
CompiledMBという名前を根拠にM_B ontologyを付与する
```

旧テストが `CompiledMB` 名を参照している場合も、検証すべき本質が

```text
candidate
→ validation
→ promotion
→ activation
```

の分離であるなら、その契約を保持したまま名称を段階移行する。

---

## 9. 最短圧縮

```text
M_B
= structure-side finite section of a SILN under B

Function
= reusable bounded operator with typed contract

CompiledFunction
= validated Function artifact

Function != M_B
```

Enterpriseの旧 `CompiledMB` 型は、現時点ではこの `CompiledFunction` の**互換実装名**として扱う。
