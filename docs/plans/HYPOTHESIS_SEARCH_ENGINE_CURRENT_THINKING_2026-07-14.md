<!--
作成日: 2026-07-14_16:04 JST
更新日: 2026-07-14_17:37 JST
-->

# 仮説探索エンジン — 現時点の意思決定メモ

記録日時: 07月14日(火)_午後4時04分22秒.

最終更新日時: 07月14日(火)_午後5時37分23秒.

## 0. この文書の位置づけ

これは、仮説生成・Kill・Backtestを一体化する構想について、現時点で妥当と考えている方向、未確認事項、停止条件を固定するための意思決定メモである。実装計画の承認、CP0の開始、専用ブランチの作成、コード変更、データ取得、legacy削除を許可する文書ではない。

現在の状態は `PRE-CP0 / PLAN-ONLY` とする。ブランチを作って開発を始めるにはまだ早い。次に必要なのは、利益機会への執着を弱めず、同時に都合のよい成功物語を排除できるよう、投資判断に必要な未確定事項を詰めることである。

## 1. 結論

目指すべきものは「仮説を大量に思いつく機能」ではない。多様な探索器を競争させ、安い反証から順に候補を殺し、誤って殺した候補も監査し、最後に残った少数へ計算資源と検証予算を集中させる、利益探索エンジンである。

攻撃性は、候補数、探索空間、再試行速度、敗者の切り捨て、勝者への資源集中に向ける。証拠基準を下げること、統計的な不都合を隠すこと、薄いデータを希望的に解釈すること、Paperやliveへ急ぐことは攻撃性ではない。それは単なる自己欺瞞である。

現状のリポジトリには、有限かつ決定論的な候補生成、手動AI packet/import、fail-closedのKill系、Backtest関連の部品がある。しかし、豊富な手法を自律的に競争させる仮説探索エンジンが完成しているわけではない。したがって、既存部品を「もう土台はできている」と過大評価せず、逆に全部を捨てるとも決めつけず、CP0で経済合理性と実装可能性を先に判定する。

### 1.1 Hostile Profit Review v2の判定

はい、前版にはまだ「あたまでっかちな理想的ナラティブ」が残っていた。主な問題は、安全性不足ではなく、
安全性を精密に書くことで利益探索の未証明部分を覆い隠せる構造だった。

- 新engineは未実装なのに、計画上は新規source 40 path、test 40 path、schema 6件まで膨らんでいた。
- 6 endogenous + 2 adapterという本数は、mechanismや市場構造の探索幅を保証しない。
- finalistだけのPBOは、K1/K2で落とした候補を含まないため、上流探索全体のoverfittingを補正しない。
- FDRは、candidate生成やthreshold調整で汚染されたp-valueを後から正常化する装置ではない。
- DSRはeffective trial数の推定方法だけで判定が動き得る。
- 小さな無層化shadow auditは、価値候補を系統的に殺すpolicyを見逃し得る。
- ASYMMETRIC/NOVELTYは期限がなければ、捨てられない物語の墓場になる。
- docs-only CP0にbranchを要求すると、調査前から開発継続へ心理的にcommitする。

したがって、現在の推奨は「巨大で正しいengineを作る」ことではない。最小のvertical sliceで現行pipelineを
直接殴り、勝てないmodule、generator、統計method、lane、engine投資を順番にKillできる構造を作ることである。

具体的には、3 core generatorから開始し、追加sourceは1件ずつ`SPIKE -> ADMIT/DISABLE/DO_NOT_BUILD`で処理する。
探索幅はgenerator数でなく、economic mechanism、information origin、decision surface、market condition、
portfolio roleのcoverageと、cell別の限界発見価値で測る。shadow auditは層化確率標本としてfalse-kill率、
上方信頼限界、economic regretを出す。研究候補にはnext falsifier、追加費用上限、expiryを課す。

攻撃性の対象は市場と仮説空間である。同時に、利益を生まない自分たちのengine、設計、統計儀式、既存投資も
容赦なくKill対象にする。

## 2. 達成したい事業的ゴール

最終ゴールは、研究成果物の数を増やすことではない。コスト、遅延、流動性、過適合、多重検定、データ品質を差し引いた後でも再現性のある利益候補を、既存方式より高い資本効率で見つけることである。

そのために、次の5領域を別々に合格させる。

1. **利益探索**
   - 複数の仮説生成手法が、同じ形式の候補契約に出力する。
   - 生成器は成果を保証されない。発見率、独自性、計算費用、下流生存率で競争し、弱い生成器は停止・縮小・廃止する。
   - 既存champion、単純benchmark、現行portfolioに対する増分価値で評価する。

2. **偽陽性排除**
   - 安価で強い反証を先に当て、高価なBacktestへ到達する候補を減らす。
   - Kill判定そのものも誤るため、kill shadow audit、非昇格の監査標本、false-kill推定を持つ。
   - 生存者だけを眺める評価は禁止する。

3. **Backtest接続**
   - 候補は、人手による意味の補完なしに、再現可能なBacktest仕様へ変換できることを要求する。
   - データ時点、特徴量時点、約定仮定、費用モデル、holdout境界を固定し、未来情報や都合のよい再計算を遮断する。
   - Backtest結果は「利益が出た」という一値ではなく、失敗条件と不確実性を含む判定材料にする。

4. **安全境界**
   - 当面の範囲はresearch/backtestまでとする。
   - Paper、live、cash、wallet、署名、取引所write、外部サービスへのデータ送信は別ゲートとし、自動昇格させない。
   - blocked状態は下流へfail-closedで伝播させる。

5. **運用可能性**
   - 同一入力・同一設定・同一コードから同一判定を再現できる。
   - epoch、試行回数、holdout消費、生成器別コスト、kill理由、Backtest資源消費を追跡する。
   - 実験名の付け替えやrunの作り直しで統計的負債をリセットできないようにする。

## 3. 現時点で採用する設計思想

### 3.1 探索器を増やすが、無条件には養わない

生成手法の豊富さは必要である。ただし、手法数そのものを成果指標にしない。初期候補としては、少なくとも次の系統を同じ候補契約へ接続できる設計を想定する。

- 既存規則・テンプレートの組合せ探索
- 時系列・横断面の変換探索
- 条件分岐・regime分割
- 特徴量相互作用と非線形構成
- イベント駆動仮説
- 反例・失敗例からの逆向き仮説
- literature、analyst、LLMなど外部起点の提案
- 既存候補の変異、交叉、局所探索

ただし最初から全系統を実装しない。deterministic adapter、typed grammar、counterfactualの異質な3 core系統で、共通契約、Kill経済性、Backtest接続が成立するかを縦に確認してから増やす。これは探索意欲を抑えるためではなく、壊れた配管へ候補だけを流し込み、計算費用と偽陽性を爆発させる無駄を避けるためである。

6 endogenous + 2 adapterはbreadth backlogであり、完成条件ではない。追加sourceは、既存3 coreに対するincremental coverage、same-budget marginal yield、false-kill regret、CPU/artifact costを改善する場合だけactive化する。

### 3.2 Killは防御機能ではなく、攻めるための資源配分装置とする

Killの役割は慎重になることではない。勝ち目の薄い候補へ使う時間を奪い、より広い探索と有望候補の厳密検証へ再配分することである。

段階は、概念的には次の順を想定する。

1. 構文・schema・再現性・データ可用性の拒否
2. look-ahead、leakage、時点不整合、重複、既知の無効形の拒否
3. 安価なproxy、subsample、摂動、負の対照による拒否
4. 多重検定、過適合、regime依存、費用感応度による拒否
5. 厳密Backtestとholdoutによる拒否
6. portfolio増分価値、容量、相関、運用制約による拒否

K1/K2相当の早期Killは、いきなり昇格権を持たせない。まずshadow modeで判定し、監査標本を厳密系へ流してfalse-kill率を測る。Kill率が高いこと自体を成功としない。価値のある候補を安く残し、価値のない候補を安く消した時だけ成功である。

### 3.3 統計手法を免罪符にしない

PBO、DSR、FDR、purged split、embargoなどは必要になり得るが、名前を並べただけでは安全にならない。適用単位、試行母数、依存構造、epochをまたぐ検定負債、holdout再利用を誤れば、精巧な数字で自己欺瞞を強化するだけである。

したがって、統計手法は次の3点を満たす場合だけ採用する。

- 何の誤りを抑える手法かが明示されている。
- 現在のデータ量と探索構造で校正可能である。
- その手法を外した場合、誤って通る候補をテストで再現できる。

固定的な「上位5%」「lane別quota」のような数値は、実データによる校正前は `INITIAL_FIXTURE_DEFAULT` と明記し、本番の正解として扱わない。

### 3.4 評価の単位を候補単体から探索システムへ上げる

探索器は、ときどき大当たりを出したという逸話では評価しない。少なくとも次を継続比較する。

- 生成候補数と重複率
- Kill段階別の生存率と計算費用
- shadow auditで推定したfalse-kill率
- 厳密Backtestへ到達した候補の質
- champion、benchmark、portfolioに対する純増価値
- 探索1単位、計算1単位、holdout消費1単位あたりの発見価値
- regime変更後の再現性と劣化速度
- 生成器を停止した場合の機会損失

改善しない生成器や複雑性は、実装済みであっても守らない。削除判断はCP11まで遅らせるが、経済的敗者を永続的に維持することもしない。

## 4. 推奨チェックポイント順序

現時点の推奨順序は次である。

`CP0 -> CP1 -> CP2 -> CP3A -> CP4 -> CP5 -> CP3B -> CP6 -> CP7 -> CP8 -> CP9 -> CP10 -> CP11`

各CPの到達状態、解禁範囲、失敗時の扱いは、
[ゴール・チェックポイント憲章](./HYPOTHESIS_SEARCH_ENGINE_GOALS_AND_CHECKPOINTS_2026-07-14.md#131-checkpoint-goal契約)
を正本とする。以下は意思決定上の要約である。

### CP0 — 投資判断に必要な実現可能性の確認

目的は設計資料を増やすことではなく、次のどれかを証拠付きで選ぶことである。

- `GO_REAL_VERTICAL_SLICE`: 実データで最小縦断を作る価値がある。
- `GO_FIXTURE_SPIKE_ONLY`: 実データ投資前に、限定fixtureで契約とKill経済性だけを検証する価値がある。
- `NO_GO`: 現状では費用、データ、識別力、実装難度が見合わない。

CP0で都合のよい結論へ寄せない。`NO_GO` は失敗ではなく、期待値の低い開発投資を止める利益保全である。

### CP1 — Contract Foundation

candidate、trial、state、partition、epoch、permission、resourceの意味を固定し、missing、invalid transition、boundary mutationをpositiveへ変換できない契約にする。ここが曖昧なら、その後の台帳、統計補正、安全境界は成立しない。

### CP2 — Program / Registry / Ledger

全生成源を共通CandidateProgramとplugin registryへ載せ、成功、失敗、重複、手動/AI介入、cross-run feedbackをappend-only ledgerへ残す。成功候補だけを記録する抜け道と、run変更による試行履歴の消去を塞ぐ。

### CP3A — 異質な最小生成器群

共通契約へ出力する、性格の異なる最小3系統程度を実装候補とする。豊富さの完成ではなく、生成器同士を比較可能にする最初の縦断である。

### CP4 — K0 Static Kill

構造不正、look-ahead、実行不能、no-op、exact duplicateをBacktest前に落とす。near duplicateはcluster化し、data不足は`DEFER_DATA`へ分離して、安さを理由に価値候補まで一律Killしない。

### CP5 — K1 Cheap Screen / Racing

安価なbaseline、cost、episode、capital、regime評価とsuccessive halvingでFull Backtest費用を節約する。同一予算のincumbent challengeと非昇格shadow auditにより、節約量だけでなくfalse-killも測る。ここが成立しなければ追加生成器へ投資しない。

### CP3B — 追加生成源の入場審査

K0/K1の経済性を確認した後で、mutation/crossover、statistical、linear model、LLMや外部trialのimport adapterをsource別に審査する。接続できたことではなく、同一予算でcoverageまたは増分発見価値があることを要求する。実装したが価値を示せない源は`IMPLEMENTED_DISABLED`とする。

### CP6 — K2 Bias Kill

全trial、候補依存、epoch跨ぎ、validation/holdout消費を含めてselection biasを攻撃する。PBO、DSR、dependency-aware FDRなどは対象riskと前提に合わせて校正し、推定不能をPASSへ捏造しない。shadow auditでfalse survivorとfalse killの双方を測る。

### CP7 — Full Backtest / Existing Kill Adapter

K2 survivorだけをlossless bindingで候補単位のFull Backtestと既存Kill chainへ接続する。費用、execution evidence、capacity、capital collision、tail、既存portfolioへの限界寄与まで通し、単体Sharpeだけでは採用しない。

### CP8 — Orchestration / CLI / Resource Calibration

全stageを決定的、再開可能、atomic、resource-boundedな運用導線へ統合する。生成器別、epoch別、Backtest別の予算とstop-lossを実測校正し、成果の出ない探索を「もう少し」で延命しない。

### CP9 — Migration / Docs / Rollback Rehearsal

legacy callerとartifactをinventoryし、新reader、dual-read、deprecation、rollbackを旧導線を削除せずrehearsalする。未知callerや互換性不明を残したままcutoverへ進まない。

### CP10 — E2E / Hostile Verification

改ざん、欠損、汚染、全滅、crash/resume、resource不足を含む敵対条件で、ゴール1〜5とfail-closed連鎖を検証する。dogfoodを行う場合も明示実行・限定予算・事前登録した損切り条件を要求し、fixtureの成功を利益証明へ昇格しない。

### CP11 — legacy置換・削除判断

新経路が実測で優位と確認され、移行とrollbackが成立した後だけlegacyを削除する。新設計への期待だけで、既存の強固なKill機能を先に壊さない。

## 5. 現時点の非交渉条件

- branch、コード、依存、schema、データ取得はまだ変更しない。
- fixtureだけで全エンジン完成を宣言しない。
- 実データがない状態で利益性能を主張しない。
- 候補数、Kill率、Backtest件数を利益発見の代理指標として単独使用しない。
- 生存者だけを評価しない。killされた候補の監査標本を残す。
- holdoutを探索のたびに再利用しない。
- run名、branch名、設定名の変更で試行回数をリセットしない。
- blocked、invalid、incompleteをreadyへ丸めない。
- research/backtestの成功をPaper/live/cash readinessへ読み替えない。
- 新方式が優れているという証拠が出る前にlegacyを削除しない。
- sunk costを理由に生成器、統計処理、基盤を温存しない。

## 6. 現在わかっている不足と誤謬リスク

### 6.1 CP0そのものが未実施

CP0 feasibility reportはまだ作成していない。したがって、実データ縦断へ進む価値、fixture spikeだけに限定すべきか、計画自体を止めるべきかは未判定である。

### 6.2 データ量と現実性の不足

現在確認されている小規模fixtureや限定episodeは、配線、schema、決定性、fail-closed挙動の検証には使えても、利益探索力の証明には使えない。大容量攻撃データや十分な市場局面が利用可能であるという前提も置かない。

### 6.3 経済的な基準が未固定

primary economic estimand、champion、単純benchmark、現行portfolio、許容turnover、費用モデル、容量、最大探索予算、stop-lossが固定されていない。ここを後付けにすると、結果に合わせて勝利条件を動かせる。

### 6.4 統計的な試行負債が未設計

候補の親子関係、生成器間依存、epoch跨ぎ、再試行、holdout再利用をどの単位で数えるかが未確定である。単純な候補件数だけでは実効試行数を表せない。

### 6.5 Killの強さを過信する危険

既存Kill機能が強固でも、新しい候補分布に対してfalse-killが低い保証はない。過去の安全性を、新探索空間へ無条件に外挿しない。

### 6.6 LLMを発想力の代用品にする危険

LLMは候補源の一つにはなり得るが、もっともらしい重複仮説を大量生産し、試行回数と検証費用を膨らませる可能性がある。LLM導入自体を進歩と数えず、独自性と増分発見価値で入場審査する。

### 6.7 運用可能性を後回しにする危険

探索ロジックだけを先に作ると、lineage、予算、再現、失敗伝播が後付けになり、利益主張を監査できなくなる。候補契約と試行台帳は探索手法より先に必要である。

## 7. 実装前に答えるべき質問

以下は重要だが、この文書作成を止める質問ではない。CP0着手の前、またはCP0の調査項目として明文化する。

1. 最優先で最大化する経済指標は何か。候補単体のrisk-adjusted returnか、portfolioへの純増価値か、探索費用あたりの発見価値か。
2. 比較対象となるchampion、単純benchmark、現行portfolioを何に固定するか。
3. 開発時間、データ取得、計算資源、holdout消費にどこまで予算を使い、何をもって損切りするか。
4. 現在利用可能な実データで、どの市場、期間、粒度、費用、regimeを検証できるか。
5. データ取得や外部送信を伴う場合、どこまで明示的に許可するか。
6. 初期pilotで許容するfalse-kill上限、false-discovery上限、計算費用上限をどう校正するか。
7. 成果が出ない場合に、生成器、Kill、Backtest、データのどこを停止し、どこまで作り直すか。

## 8. 直近の判断

今は専用branchを作らない。CP0も開始しない。コード実装、data取得、依存変更、schema変更、legacy削除を行わない。

次に行う価値があるのは、この意思決定メモと既存のゴール・チェックポイント文書を突き合わせ、次の2点を確定することである。

1. CP0で答えが出れば投資判断できる、最小の質問集合になっているか。
2. `GO_REAL_VERTICAL_SLICE / GO_FIXTURE_SPIKE_ONLY / NO_GO` の判定条件が、結果を見てから動かせない形になっているか。

この2点が固まる前のbranch作成は、実装開始を既成事実化し、sunk costによって `NO_GO` を選びにくくする。したがって、現在は計画の批判的レビューと未確定事項の圧縮を優先する。

## 9. この文書を更新する条件

次のいずれかが起きた場合、この文書の `更新日` と可視タイムスタンプを更新し、判断の変更理由を追記する。

- primary economic estimandと比較対象が決まった。
- 探索予算、データ予算、計算予算、stop-lossが決まった。
- CP0の開始が明示的に承認された。
- feasibility調査で前提が崩れた。
- CP0が `GO_REAL_VERTICAL_SLICE / GO_FIXTURE_SPIKE_ONLY / NO_GO` のいずれかを判定した。
- branch作成または実装開始を正当化する証拠が揃った。

現時点では、構想は有望だが未検証である。貪欲に利益を探す価値はある。しかし、利益が存在すること、現在のデータで識別できること、既存方式より安く見つけられることのどれも、まだ証明されていない。この不都合な事実を維持したまま、次の判断を行う。
