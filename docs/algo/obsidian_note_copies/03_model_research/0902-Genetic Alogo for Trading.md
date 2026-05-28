
# how to actually build a genetic algo for trading
![](https://img.youtube.com/vi/-m_vDpdLfVk/maxresdefault.jpg)



[Source URL](https://www.youtube.com/watch?v=-m_vDpdLfVk)

## 遺伝的アルゴリズムの概要と利点
- 遺伝的アルゴリズムは、生物学から発想を得たもので、複数の戦略を交配させて新しい戦略を生み出すことで機能します。[(00:00:35)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=35s)
- 遺伝的アルゴリズムは、単純な演算子（プラス、マイナス、掛け算、割り算など）や移動平均などのテクニカル指標を組み合わせて、シグナルや戦略を開発するために使用できます。[(00:05:46)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=346s)
- 遺伝的アルゴリズムは、膨大な量のデータを分類して最適化する、シンプルだが強力な方法です。[(03:13:11)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=11591s)
## 遺伝的アルゴリズムの実装と考察
- 遺伝的アルゴリズムを使用する際は、過剰適合を避けるために、単純な関数を使用することが推奨されます。[(00:07:47)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=467s)
- トレーディング戦略の堅牢性を確保するため、サンプルテストを実施する。同様の二重盲検テストアプローチを実装して、目に見えないデータモデルの解釈に対して戦略が一般化することを確認する。 [(00:08:01)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=481s)
- モデルの説明方法を検討する。特に、投資家に提示またはプレゼンテーションする場合。更新と再構築。GPモデルは再構築が必要になる場合があることに留意する。 [(00:08:13)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=493s)
- 目標は、人間の脳では思いつかないような100万[(00:18:13)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1093s)個の戦略[(00:18:06)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1086s)を出力することです。[(00:18:17)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1097s)
- 長期データで最適化された戦略を短期データに適用する場合、データをより長い時間枠（5分、15分、または1時間）にリサンプリングすることを検討する。 [(02:15:07)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=8107s)
- データフレームの列名が要件と一致しない場合は、列名を調整する必要がある。 [(02:21:55)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=8515s)
## 遺伝的アルゴリズム vs. 他の最適化手法
- GASは、EMAの期間など、固定された戦略[(00:16:31)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=991s)の枠組みの中でパラメータ[(00:16:29)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=989s)を最適化すること[(00:16:26)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=986s)に重点を置いている場合に適しています。GESは、さまざまなオペレータ[(00:16:45)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1005s)を組み合わせた、まったく新しい取引ルール[(00:16:42)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1002s)や式[(00:16:42)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1002s)を進化させたい場合に適しています。
- 遺伝的アルゴリズム（GA）と文法的進化（GE）はどちらも進化型アルゴリズムだが、潜在的な解決策の表現と進化の方法が異なる。GAは通常、問題に対する潜在的な解決策を表すために、固定長の文字列（多くの場合バイナリだが、必ずしもそうとは限らない）を使用する。これらの文字列は、染色体と呼ばれることが多い。GEは、遺伝子型から表現型へのマッピングアプローチを使用する。これは、事前定義された文法に基づいて、構文的に正しいプログラムまたは式にマッピングされる、整数またはその他の単純な構造の文字列を進化させる。 [(00:13:02)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=782s)
- GEは、文法[(00:20:16)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1216s)に従って異なる要素[(00:20:39)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1239s)を組み合わせることで、膨大な数の可能な[(00:20:36)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1236s)戦略[(00:20:32)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1232s)を探索することができます。[(00:20:29)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1229s)
- 微分進化は、年利回りを最適化する適合度関数を持ち、ベクトル差を使用して個体を摂動させることによって探索と活用のバランスをとることに焦点を当てています。 [(00:30:18)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1818s)
- 粒子群最適化は、年利回りを最適化する適合度関数を持ち、パーソナルベストとグローバルベストによって駆動される検索空間を通じて粒子戦略の動きをシミュレートすることに焦点を当てています。 [(00:30:47)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1847s)
- 標準的な遺伝的アルゴリズムは、ソートino比と最大ドローダウンのペナルティを組み合わせた適合度関数を持ち、高いソートino比と低いドローダウンを持つ戦略を特にターゲットにして、リターンとリスクのバランスをとることに焦点を当てています。 [(00:31:13)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=1873s)
- 遺伝的アルゴリズムとバックtesting.pyのグリッドサーチはどちらも最適化手法だが、探索空間、適応性、探索と活用のバランス、連続パラメータの処理、解釈可能性という重要な違いがある。 [(02:52:10)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=10330s)
- グリッドサーチは、事前に定義されたパラメータ値のすべての組み合わせを徹底的にテストするのに対し、遺伝的アルゴリズムはパラメータ空間をより動的に探索し、明示的に定義されていない解決策を見つける可能性がある。 [(02:52:18)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=10338s)
- グリッドサーチは、特にパラメータが多い場合や値の範囲が広い場合は、計算コストが高くなる可能性があるが、遺伝的アルゴリズムは、考えられるすべての組み合わせをテストするわけではないため、大規模なパラメータ空間ではより効率的であることが多い。 [(02:52:43)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=10363s)
## 特定のコード実装と問題解決
- 提供されたコードは、バックトレーダーフレームワーク内で、Golfと呼ばれるカスタム戦略に基づいて取引戦略を最適化する遺伝的アルゴリズムを実装しています。[(00:37:53)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=2273s)
- このコードは、シャープレシオ、ドローダウン、ROIなどの指標を考慮した多目的適合度関数を使用して、過去の市場データに対するパフォーマンスを評価することで戦略を評価します。[(00:38:20)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=2300s)
- バックトレーダーフレームワークは、戦略の実行とバックテストに使用されます。これは、包括的なバックテストと分析のための強力なツールです。[(00:40:16)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=2416s)
- 提供されたコードは、BTC データを CSV から読み込み、バックテスト用に準備します。[(00:43:33)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=2613s)
- このコードは、遺伝的アルゴリズムを実装して、ビットコインの取引戦略を最適化します。過去の価格データとバックテストを使用して適合性を評価します。 [(00:46:25)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=2785s)
- コードは `if __name__ == "__main__":` ブロックで囲む必要があります。これは、スクリプトがモジュールとしてインポートされたときにマルチプロセッシングコードが実行されないようにするためです。 [(00:48:00)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=2880s)
- pandas データフレーム内の範囲外のインデックスにアクセスしようとしたため、`backtesting_indicators.py` の `stock_RSI` 関数で問題が発生しています。これは通常、データフレームが空であるか、予想よりも行数が少ないために、存在しないデータにアクセスしようとした場合に発生します。 [(00:52:56)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=3176s)
- エラーメッセージは、RSI 計算が系列ではなくデータフレームを返すことを示しているため、`cal_RSI` に `.apply` を追加する必要があります。 [(01:06:53)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=4013s)
- `cal_RSI` は datetime 列に対して操作を実行しようとしていますが、これはサポートされていません。関数を変更して数値データを処理する必要があります。 [(01:01:10)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=3670s)
- ユーザーは、データフレームが空であるという問題をデバッグするために、"get kpi" 関数に追加のデバッグ情報を追加することを提案されました。 [(01:08:54)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=4134s)
- ユーザーは、"apply to entire file" と "regular apply" の違いを質問しました。 [(01:16:17)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=4577s)
- コードは正常にデータをロードできるようになり、進展が見られました。 [(01:16:58)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=4618s)
- 動画投稿者は、視聴者からのフィードバックに応答して、遺伝的アルゴリズムの進捗状況の視覚化を改善し、冗長な計算を減らすために、いくつかの変更を加える必要があると述べている。具体的には、`kpi`関数を変更して結果をキャッシュし、冗長な計算を減らすことを提案している。 [(01:52:57)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=6777s)
- 出力はジェネティックアルゴリズムの進捗レポートからのもので、世代番号、評価された新しい個体の数、集団全体の適合度の平均値、適合度関数の標準偏差、集団の最小適合度値、集団の最大適合度値が表示される。 [(02:04:42)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7482s)
- すべてのシャープレシオがゼロになっているのは、戦略が全く取引を行っていないか、シャープレシオの計算に問題があることを示唆している可能性がある。 [(02:06:47)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7607s)
- すべてのドローダウンが100に近く、または完全に100になっている。これは、考えられる最悪のドローダウンである。 [7620]
- すべてのROIは-100である。 [(02:07:07)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7627s)
- 適合度の計算方法、初期集団の作成方法、取引戦略の実装方法、またはデータとの相互作用方法に問題がある可能性がある。 [(02:07:15)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7635s)
- 100%のドローダウンを示している場合、実際に取引は行われているが、すべてのお金を失っていることになる。これは、1分データという短期間での取引が多すぎるためである可能性が高い。 [(02:14:35)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=8075s)
- ジェネティックアルゴリズムの世代3では、最初のコンポーネントであるシャープレシオがプラスになり、2番目のコンポーネントであるドローダウンが88から43に減少し、3番目のコンポーネントが84から-19に改善した。[(02:44:09)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=9849s)
- このアルゴリズムでは、k分割交差検定を使用して、取引戦略の堅牢性を確保している可能性が高い。[9975]
- fold 1の最適な個体（67、23、68、60、1）は、fold 1で見つかった最適なパラメータセットを示しており、これらのパラメータは、その特定のfoldで最高のパフォーマンスを発揮した取引戦略に対応している。[(02:47:07)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=10027s)
## 遺伝的アルゴリズムの市場予測への応用
- 遺伝的アルゴリズムは、過去15年間で多くの興味深いバリエーションが設計・実装され、数値モデリングのコンピュータによるソリューションとして、強力な探索および最適化スキームであることが証明されている。 [(03:08:34)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=11314s)
- 遺伝的アルゴリズムは、従来のトレンド分析を、複雑な国際経済において、より広範な予測を行うための実用的な手段に変えることを目的としている。[(03:14:47)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=11687s)
- 多くの予測モデルは、経済指標間の関係性を推測することになる。[(03:15:54)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=11754s)
- 遺伝的アルゴリズムの予測における価値は、多くの潜在的な関係性を提案し、その予測の成功率をテストできる点にある。 [(03:16:05)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=11765s)
- 株式平均を予測するために選択された変数は、経済価格、過去の価格行動、S&P市場の幅（騰落銘柄数で表される）、ボラティリティまたは上下トレンドの強さなど、経済の基本的な性質を反映している。 [(03:16:31)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=11791s)
- 週次の値が頻繁に改訂されず、指数が重複したり強く相関したりする傾向がないため、これらの経済指標は有望である。 [(03:18:24)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=11904s)
- S&P株価平均は、モデル14において、一連の経済変数を反映している。 [(03:00:16)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=10816s)
- 金価格（変数1）が非常に高く、長期国債価格（変数2）が低く、NASDAQ総出来高（変数3）が安定している場合、S&P 500の終値は上昇する可能性がある。 [(03:00:52)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=10852s)
- 株式平均におけるトレンドを分析する際、金価格をインフレ、ひいては株式平均への影響を測る指標として用いることができる。 [(03:26:05)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=12365s)
- 遺伝的アルゴリズムは、膨大な数の取引ルールを検証し、そのパフォーマンスを評価することで、最も効果的な取引ルールを抽出し、将来の世代に受け継がせることができる。 [(03:26:19)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=12379s)
- 遺伝的アルゴリズムは、NASDAQやNYSEの取引量などの単純な指標と比較して、10倍から100倍も優れたパフォーマンスを発揮する、より洗練された取引ルールを提供する。 [(03:34:22)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=12862s)
- 遺伝的アルゴリズムは、S&P 500 の取引ルールを最適化するために使用されます。 [13554]
- 遺伝的アルゴリズムは、他の AI 技術とは異なり、取引シグナルだけでなく、特定の取引が最適である理由についての洞察も提供し、予測力と解釈可能性の両方を提供します。 [(03:45:32)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13532s)
- 遺伝的アルゴリズムは、取引ルールを進化させ、トレンドの変化を検出し、資産の最適な組み合わせを確立できる強力なツールです。 [(03:45:18)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13518s)
- 履歴データは、14 の市場変数を含む複数の経済指標を考慮しています。GA は、インフレ率、金利、株価のボラティリティ、市場の幅など、14 の変数を分析して、将来の S&P 500 の動きを予測するための最適な組み合わせを見つけます。 [(03:45:57)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13557s)
- GA は、クロスオーバー（2 つのソリューションの一部を組み合わせること）と突然変異（ランダム性を導入してより良いソリューションを進化させること）を使用して、局所最適化と均質性の落とし穴を回避します。 [(03:46:26)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13586s)
- GA は、経済指標とその S&P 500 への影響の間の時間ラグを考慮し、ラグウィンドウを最適化して予測精度を高めます。 [(03:46:40)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13600s)
- このモデルは、経済指標に関する週次データを使用し、最適な 3 つの変数を最適化します。取引ルールは、市場への短期および長期の両方の影響を考慮します。 [(03:47:07)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13627s)
- GAベースの戦略は、複数の要因を効率的に組み合わせ、最適化することにより、従来の単一変数取引ルールやその他の AI メソッドよりも優れています。 [(03:47:33)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13653s)
- この論文では、GA アプローチを国際通貨やコモディティなどの他の市場に拡張して、収益性の高い取引ルールを発見することを提案しています。 [(03:47:59)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=13679s)
## 個人的な見解や経験談
- 動画投稿者は、1日に約20個のOpen AIクォータを使用できることを強調しています。 [(01:17:21)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=4641s)
- 動画投稿者は、視聴者に毎日Twitchライブストリームに参加して、詳細な情報を取得するように勧めています。 [(01:19:59)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=4799s)
- 動画投稿者は、トレーディングへの情熱をコーディングに注ぎ込み、毎日RBIシステムの調査、バックテスト、ボットへの実装に取り組んでいると述べています。 [(01:21:37)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=4897s)
- Moon Dev よりも熱心にアルゴリズムトレーディングに取り組んでいる人がいる。 [(01:27:57)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=5277s)
- Moon Dev は、テクノロジー業界で燃え尽き症候群を訴える人は、実際には情熱を持っていない人だと考えている。 [(01:31:10)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=5470s)
- Moon Dev は、視聴者に対して、燃え尽き症候群を言い訳にせず、自分が本当にやりたいことをするように勧めている。 [(01:32:09)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=5529s)
- AFXは、誰かに「燃え尽き症候群」という言葉を使ったり、燃え尽き症候群になる可能性を指摘されたりすることに腹を立てている。 [5648]
- AFXは、Factory of Gamingという名前のAIを搭載したコーディング支援ツール「Cursor」を使用している。 [(01:36:44)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=5804s)
- AFXは、CursorがSonetで1日16～17件の無料リクエストを提供していることに言及し、コーディングに役立つと考えている。 [5981]
- Mev は、数ヶ月間取り組んできた遺伝的アルゴリズムに取り組んでいる。そのアイデアは、変数を入力し、無制限の取引戦略を出力することである。 [6245]
- Mev は、視聴者が彼のボットやコードではなく、アイデアを取り上げて探求してくれることを望んでいる。 [(01:44:19)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=6259s)
- 視聴者は、証明された優位性がない限り、レベレッジをかけて取引したり、手動で取引したりするべきではない。 [6324]
- Ry bear は、John Bollinger がポッドキャストを配信していると考えている。 [(01:46:19)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=6379s)
- AFX が動画投稿者にハートを送った。これは、ブロックされたくないからである。 [(01:49:17)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=6557s)
- ニューヨークで働いている、またはファンドで働いている視聴者に向けて、今すぐ仕事をやめるべきだと述べている。特に、動画投稿者のライブストリームを視聴してアイデアを得るように指示されている場合は、なおさらである。 [(01:49:53)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=6593s)
- Factory of gamingは、機械学習を使ったトレーディング手法を試したが、約50%の精度しか得られなかったと述べている。[(01:56:02)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=6962s)
- meyは、キャンドルレンジ理論と流動性スイープスナイパーの技術を組み合わせたCRTボットを構築した。[(02:02:11)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7331s)
- meyは1週間前にコーディングを始め、PythonとMQL5をゼロから学んだ。[7342]
- Rは現在2～3で、ストップロス調整によって勝率を上げようとしている。 [(02:02:28)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7348s)
- meyの取引の時間枠はH1とM1のエントリーである。 [(02:02:53)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7373s)
- ryer factoryは、ジェネティックアルゴリズムには非常に正確なデータが必要だが、1分足のローソク足しかないため、ボットの精度が少し低くなると述べている。 [(02:03:05)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=7385s)
- Moon Algotrade.com にメールすると、暗号通貨でコースを購入できる。 [(02:24:56)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=8696s)
- Blood Money さんの質問に対し、コーディングのオンラインコースの料金は 69 ドルであると回答しています。[8859]
- また、仮想通貨での支払いは moonalgotcam.com で連絡すれば可能であると回答しています。[(02:27:46)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=8866s)
- さらに、視聴者からの「5,000ドルでボットを始めるのに十分か」という質問に対し、十分ではなく、少なくとも1年間は調査とバックテストを繰り返すべきだと回答しています。[(02:31:02)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=9062s)
- あるユーザーが、コーディングを学ぶこと、そして大企業と競争することがいかに難しいかについてコメントした。 [(02:37:29)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=9449s)
- これに対し、動画投稿者は、コーディングは「優れた均衡力」であり、コーディングを学ぶことで誰でも何かを構築できると反論した。 [(02:39:41)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=9581s)
- また、動画投稿者は、AirbnbやUberなどのスタートアップ企業を引き合いに出し、大企業と競争することが可能であることを主張した。 [(02:42:12)](https://www.youtube.com/watch?v=-m_vDpdLfVk&t=9732s)


# hidden markov model 4 trading (jim simons fav)
![](https://img.youtube.com/vi/A6F0FfM3NFg/maxresdefault.jpg)



[Source URL](https://www.youtube.com/watch?v=A6F0FfM3NFg)

## Introduction to Hidden Markov Models (HMM) in Trading [(00:00:00)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=0s)
- 隠れマルコフモデル（HMM）は、観察できない隠れた状態を持つシステムを記述するために使用できる統計モデルです。金融では、これらの隠れた状態は、市場レジームや経済状況を表すことができます。 [(00:01:06)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=66s)
- HMMは、観測可能な結果（価格の動きなど）に基づいて、システムの隠れた状態を推測するために使用できます。 [(00:01:40)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=100s)
- トレーダーは、これらの隠れた状態間の遷移の確率と、各状態で特定の結果を観察する確率を推測することにより、将来の市場の動きを予測できます。 [(00:01:50)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=110s)

## Overview of Jim Simons' Use of HMMs [(00:09:15)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=555s)
- 複数の市場レジームを特定することに焦点を当て、ジム・シモンズ氏が頻繁に議論するように、さまざまな特徴も組み込みます。[(00:17:07)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1027s)
- 機械学習における特徴エンジニアリングの重要性を強調するために、さまざまな特徴も組み込みます。[(00:17:35)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1055s)
- ビットコインのエコシステムHMM。仮想通貨市場をエコシステムとして想像してみましょう。[(00:17:40)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1060s)

## Understanding the Hidden States in Financial Markets [(00:17:45)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1065s)
- 隠れマルコフモデルは、観察可能な市場指標に基づいて、市場の隠れた状態を識別するために使用できます。たとえば、ビットコインの場合、これらの状態は砂漠（高ボラティリティ、低ボリューム、中程度の活動アドレス）、森林（中ボラティリティ、高ボリューム、高活動アドレス）、海（低ボラティリティ、高ボリューム、低活動アドレス）、ツンドラ（低ボラティリティ、低ボリューム、低活動アドレス）として特徴付けることができます。 [(00:18:15)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1095s)
- イーサリアムの場合、HMMを使用して、ブーム（強い正の勢い、高いガス料金、増加するETHロック）、不況（強い負の勢い、低いガス料金、減少するETHロック）、回復（弱い正の勢い、中程度のガス料金、安定したETHロック）、停滞（弱い勢い（正または負）、低いガス料金、安定したETHロック）などの隠れた経済サイクルを識別できます。 [(00:18:56)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1136s)
- カルダノの場合、HMMは、強気（一貫したプラスのリターン、高いプラスのソーシャルメディア活動、ステーキング率の上昇）、弱気（一貫したマイナスのリターン、高いマイナスのソーシャルメディア活動、ステーキング率の低下）、中立（小規模なプラスまたはマイナスのリターン、低いソーシャルメディア活動、安定したステーキング率）、躁状態（極端なプラスまたはマイナスのリターン、非常に高いソーシャルメディア活動のボラティリティ、ステーキング率）などの隠れたセンチメント状態を明らかにすることができます。 [(00:20:00)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1200s)
- Uniswapの場合、HMMを使用して、洪水（高いTVL、低いVelocity、大きな平均取引サイズ）、干ばつ（高いTVL、低いVelocity、小さな平均取引サイズ）、小川（中程度のTVL、中程度のVelocity、中程度の取引サイズ）、急流（高いTVL、高いVelocity、さまざまな取引サイズ）などの隠れた流動性体制を特定できます。 [(00:21:13)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1273s)
- Polkadotの場合、HMMは、イノベーション（少数のプロジェクト、集中型のトークン配布、低いオークション参加）、アーリーアダプション（増加するプロジェクト数、拡大する配布、中程度のオークション参加）、アーリーマジョリティ（多くのプロジェクト、広く配布されたトークン、高いオークション参加）、レイトマジョリティ（安定したプロジェクト数、非常に幅広いトークン配布、減少するオークション参加）などの隠れた技術採用段階を識別できます。 [(00:22:47)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1367s)

## Applying HMM to Algorithmic Trading Strategies [(00:26:30)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1590s)
- 隠れマルコフモデル（HMM）は、価格や出来高などの観測可能な市場の特徴に影響を与える、市場に隠れた状態やレジームがあると仮定しています。 [(00:26:53)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1613s)
- HMMには、強気、弱気、横ばいなどのさまざまな市場レジーム（隠れた状態）、測定可能な市場データ（観測可能な特徴）、状態間を移動する可能性（遷移確率）、各状態で特定のデータを観測する可能性（出力確率）などの主要な要素があります。 [(00:27:06)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1626s)
- HMMは、複雑な市場のダイナミクスを捉え、変化する市場の状況に適応し、意思決定のための確率的枠組みを提供できるため、トレーディングにおける資産配分、リスク管理、エントリー/エグジットタイミング、ポートフォリオのリバランスに適用できます。 [(00:27:49)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=1669s)

## Case Study: Using HMM in Cryptocurrency Markets [(00:38:50)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=2330s)

## Conclusion and Practical Tips for Implementing HMMs [(00:48:05)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=2885s)
- AI を活用したコーディングは、学習に比べてゲーム感覚で取り組めるため、比較的容易である。 [(00:50:30)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=3030s)
- トレードの自動化を学ぶには、独学でもオンラインの教材やブートキャンプなどを活用して、集中的に学習する必要がある。 [(00:51:12)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=3072s)
- 誰もが簡単に利益を上げられるわけではないが、AI の活用により、誰でもトレーディングに挑戦できる環境が整っている。 [(00:53:31)](https://www.youtube.com/watch?v=A6F0FfM3NFg&t=3211s)

# High Performing Trading Strategies with Genetic Programming
![](https://img.youtube.com/vi/wZ9_xDP2Anc/maxresdefault.jpg)



[Source URL](https://www.youtube.com/watch?v=wZ9_xDP2Anc)

## 1970年代と1980年代の取引戦略の変化
- 1970年代には、移動平均クロスオーバーシステムが最先端とされ、単純なテクニカル指標を用いて収益性の高い戦略を開発することは比較的容易であった。[(00:00:24)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=24s)
- 1980年代後半のパソコンの出現と時を同じくして、そのような単純な戦略は失敗し始めた。[(00:00:55)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=55s)
- 1980 年代までに、データの入手可能性、分析ツール、コンピューティング能力の向上により、単純な取引戦略は効果が薄れました。 [(00:19:14)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=1154s)
## 遺伝的プログラミング（GP）を用いた取引戦略の開発
- 遺伝的プログラミングを用いた初期の経験では、ニューヨーク市のイェシーバー大学の神経科学部長であったハフトン・エEOL（Hfton e EOL）と協力し始めた。[(00:02:03)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=123s)
- ハフトンは、遺伝子研究で膨大かつ非常に複雑なデータセットを分析するために広く使用されている種類の技術を応用して、取引戦略を作成することを提案した。[(00:02:25)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=145s)
- ハフトンと私は、後にプロトン（Proton）ファンドとなるものを設立するために協力した。[(00:04:14)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=254s)
- 遺伝的プログラミングは、データ構造内のパターンやルールを特定するために非常に一般的な方法で使用できる、進化ベースのアルゴリズム的方法論である。[(00:05:51)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=351s)
- 取引戦略の文脈では、データの観測には、価格データだけでなく、価格のボラティリティ、移動平均、およびその他のさまざまなテクニカル指標も含まれる可能性がある。[(00:06:23)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=383s)
- 過剰適合の危険性を減らすために、システムが使用できる関数のタイプを加算、減算、除算、乗算、指数、三角関数などの単純な演算子に限定するのが通例である。[(00:06:52)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=412s)
- この例では、GPシステムは、いくつかの単純な演算子とサインとコサインの三角関数を組み合わせて、2つの変数XとYの式を含むシグナルを作成している。[(00:07:29)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=449s)
- GPプロセスにおける進化的側面は、既存のシグナルまたはモデルを、ツリーの分岐のノード、または分岐全体を別の分岐に置き換えることによって変異させることができるという考え方に由来する。[(00:07:50)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=470s)
- 過去15年間で、遺伝的プログラミング（GP）の理論と実践の両面で大きな進歩が見られ、単一のハイパースレッドCPUを使用することで、以前は50台のネットワークCPUを搭載したクラスターでしかできなかった速度をはるかに上回る速度で、GPシステムがシグナルを生成できるようになりました。 [(00:08:38)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=518s)
- 遺伝的プログラミング（GP）は、加算、減算、指数、三角関数などの単純な演算子を使用して、データ構造内のパターンやルールを識別する進化ベースのアルゴリズムです。 [(00:19:42)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=1182s)
- GP モデルは新しいデータで更新するのが難しく、多くの場合、最初から再構築する必要があり、そのたびに非常に異なる結果が生み出されます。 [(00:16:54)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=1014s)
## GPで開発された日中取引システムのパフォーマンス結果
- GPで開発された日中取引システムの パフォーマンス結果は、原油（CO）、ユーロ（EC）、E-mini S&P 500（ES）、金（GC）、ヒーティングオイル（HO）、コーヒー（KC）、天然ガス（NG）、10年債ノート（TY）、債券（US）の9つの異なる先物市場を取引しています。 [(00:09:20)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=560s)
- このシステムは、2006年から2011年までの15分足のデータを使用して構築され、2012年から2014年までのアウトオブサンプルデータでテストされました。 [(00:10:25)](https://www.youtube.com/watch?v=wZ9_xDP2Anc&t=625s)


# how to actually have ai work for you 24/7 (w/ agent zero)
![](https://img.youtube.com/vi/DUO6O_efLNc/maxresdefault.jpg)



[Source URL](https://www.youtube.com/watch?v=DUO6O_efLNc)

## AIエージェント：Agent Zero
- AIを使って、YouTube動画を見て取引戦略を見つけ出し、その戦略に基づいてバックテストのコードを作成する。 [(00:00:59)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=59s)
- バックテストのリサーチ、コーディング、デバッグ、実行を行うには、複数のAIが必要になる可能性がある。 [(00:04:18)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=258s)
- プログラミングの知識がなくても、Agent Zero を使用することで誰でも簡単に AI エージェントを構築できる。 [(00:13:34)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=814s)
- Agent Zero は、コードの記述、ターミナルの使用、エラーの修正、他の AI エージェントの起動など、完全に自律的に動作する新しい AI エージェントである。 [(00:13:52)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=832s)
- Agent Zero は、特定のタスク用にプログラムされていない、動的に成長し学習するように設計された汎用パーソナルアシスタントです。 [(00:17:16)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=1036s)
- Agent Zero は、以前の解決策、コード、事実、指示などを記憶することで、将来のタスクをより迅速かつ確実に解決します。 [(00:19:43)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=1183s)
- Agent Zero フレームワークは高度にカスタマイズ可能で拡張可能です。ユーザーはシステムプロンプトを変更することで動作を変更できます。 [(00:21:17)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=1277s)
- Agent Zero は、ユーザーがリアルタイムで読み取り、介入できる、明確でカラフル、かつインタラクティブな出力を生成します。出力は自動的に HTML ファイルとログフォルダーに保存されます。 [(00:23:32)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=1412s)
- Agent Zero は、Docker コンテナなどの隔離された環境で実行することをお勧めします。これは、適切な指示があれば、コンピューター、データ、またはアカウントに損害を与える可能性があるためです。 [(00:24:08)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=1448s)
- フレームワークを実行するには、Python をシステムにインストールする必要があります。また、エージェントにはインターネットアクセスが必要です。 [(00:26:38)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=1598s)
- 視聴者からの質問に対し、Agent Zeroは必要に応じてDockerを自動的に使用することを説明する。 [(00:55:41)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3341s)
- Agent Zero は、Open AI、Anthropic、Perplexity の3つの API キーを使用して初期化される。 [(00:57:11)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3431s)
- Agent Zero は、「stats」フォルダが見つからないため、タスクの実行に問題が発生したと報告しました。必要なファイルが環境にアップロードまたはコピーされていない可能性があると示唆しています。 [(01:31:52)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=5512s)
- Agent Zero は、必要なファイルを含むディレクトリ構造にアクセスして書き込むことができますが、「strategist」フォルダとファイルは存在しません。 [(01:34:00)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=5640s)
- プレースホルダーデータが使用されていたため、Agent Zero はタスクを完了することができました。 [(01:36:16)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=5776s)
- Agent ZeroはDockerコンテナ内で動作しており、ユーザーのローカルマシン上では動作していない。 [(01:44:32)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=6272s)
- Agent ZeroのDockerコンテナには、ユーザーのローカルディレクトリに対応するボリュームがマウントされていないようだ。 [(01:47:08)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=6428s)
- Agent Zeroは、デバッグを行い、メッセージのクリーンアップと要約を提供しています。 [(02:09:11)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=7751s)
- これまでのところ、940,000トークンが使用され、359ドルの費用が発生しています。 [(02:09:54)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=7794s)
- Agent Zeroは、バックテスト中に古い統計を使用しないように指示されています。 [(02:10:29)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=7829s)
- Agent Zeroは、指示に従わず、古い統計を削除するように再度指示されます。 [(02:12:08)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=7928s)
- Agent Zero はタスクを実行するために多数のエージェント（最大37）を使用しており、その結果、API の使用量が急増している。 [(03:14:36)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11676s)
- このAIを使うのに184ドルの費用がかかり、誰でも利用できるわけではない。 [(03:18:29)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11909s)
- このAIは現在、Moeという名前のユーザーのリクエストに基づいて、取引戦略に関する論文を作成中である。 [(03:19:03)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11943s)
## トレード戦略とバックテスト
- AIを使って24時間年中無休で作業する方法を説明する。 [(00:00:03)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3s)
- Agent Zero は、オフラインとオンラインの両方の検索を組み合わせた、組み込みの知識ツールを持っている。 [(00:07:31)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=451s)
- Agent Zero は、YouTube DL、YT、FFmpeg などのライブラリをインストールして使用し、YouTube ビデオをダウンロードして MP3 に変換できる。 [(00:07:45)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=465s)
- Agent Zero は、他のエージェント（Agent 1 など）を生成し、タスクを委任してコンテキストウィンドウをクリーンに保つことができる。 [(00:09:29)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=569s)
- セキュリティ対策として、コーディングやストリーミングには別々のマシンを使用している。 [(00:12:21)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=741s)
- データサイエンスのバックグラウンドを持つ人物が、コーディングを学び始めたきっかけは、機械学習の勉強だった。[(00:40:02)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=2402s)
- 無制限の戦略、1時間、午後、15分、BTC、15分、2020、1時間、2020を使用する戦略について説明されています。[(01:13:23)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=4403s)
- pandas、pandas-ta、ta-libをインストールする必要があります。 [(01:14:48)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=4488s)
- backtesting.pyを使用して、戦略フォルダをループ処理し、バックテストを実行する必要があります。 [(01:16:11)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=4571s)
- Krishna は、バックテストを実行するために実際のデータファイルを使用する必要があることを示唆しています。 [(01:26:11)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=5171s)
- 18個の戦略が記述されたテキストファイル（.txt）が"strategies"フォルダー内にあり、各ファイルの内容を読み込んでバックテストを行い、その統計を"stats"フォルダーに出力する必要がある。[(02:03:26)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=7406s)
- 最初の戦略である"Donchian Channels"のバックテストが開始された。[(02:08:01)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=7681s)
- テキストベースの最初の戦略は、「strategy」フォルダにある。この戦略は、コードに変換してデバッグし、バックテストから統計を取得するために使用する。[(02:17:30)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=8250s)
- 話者は、視聴者の誰かが「ta-lib」という Python ライブラリをインストールする必要があると述べています。 [(02:33:40)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=9220s)
- スラープ音が聞こえるかどうかの確認後、バックテストが完了したことが述べられています。 [(02:45:15)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=9915s)
- 話者は、Agent Zero を使用して RBI システムの調査、バックテスト、実装を行いたいと考えています。また、バックテストのコーディングとデバッグも自動で行いたいと考えています。 [(02:47:46)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=10066s)
- 動画投稿者は、AIツール「Agent Zero」を使って自動売買戦略を構築しようとしているが、まだ満足のいく結果は得られていない。 [(02:54:26)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=10466s)
- これまでのところ、Agent Zeroを使ったテストでは約10ドルの費用がかかっている。 [(02:57:03)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=10623s)
- Agent Zero は約2ドルの利益を上げ、残りの試行回数は2回です。[(03:04:20)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11060s)
- Agent Zero はバックテストを実行しており、その過程で費用がかさんでいる。 [(03:10:07)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11407s)
- 今日の配信では、AIを使って430万ドルの利益を得ることができた。 [(03:18:09)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11889s)
## ライブ配信に関する情報
- Twitch のストリーミング品質は YouTube よりも優れている可能性があるという意見がある。[(00:47:32)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=2852s)
- ある視聴者から、仮想環境に API キーを追加する方法について質問があった。[(00:47:57)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=2877s)
- 多くの視聴者がチャットで「777」とコメントせず、ただ視聴しているだけである。 [(00:48:39)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=2919s)
- APIキーを非公開にするために、.envファイルにキーを追加する方法を説明する。 [(00:51:38)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3098s)
- Perplexity は検索エンジンである。 [(01:02:41)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3761s)
- 話者は、視聴者からのフィードバックに基づいて、提供されたコードに悪意のあるコードがないことを確認した。 [(01:02:27)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3747s)
- Perplexity AI はライブ検索エンジン情報にアクセスできます。 [(01:02:54)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3774s)
- 言語モデルにおける temperature パラメータは、モデル出力のランダム性または創造性を制御します。低い値はより決定論的で焦点の絞られた出力を生成し、高い値はより多様で創造的な出力を生成します。 [(01:04:41)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3881s)
- Moon モデルの temperature は 0 から 1 の範囲で、0 は最も事実に基づいたもので、1 は最も創造的なものです。 [(01:06:00)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=3960s)
- Civil は、「自分が作ったものは決して人に教えてはいけない」というルールがあると述べています。 [(01:21:36)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=4896s)
- クリスチャンは、コードベースがシンプルなので、Agent Zero のコードをさらに良くすることができると述べています。 [(01:22:21)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=4941s)
- ヒッピーは野心的ではないが、人に対して親切で、良い価値観を持っている。 [(01:39:04)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=5944s)
- クリスチャンは、現在の作業ディレクトリを確認するために「PWD」を実行するように指示しました。 [(01:48:19)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=6499s)
- クリスチャンは、エージェントKに「PWD」と入力して、作業ディレクトリを確認するように依頼しました。 [(01:56:02)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=6962s)
- シビルは、CTFがハッキングとソフトウェア開発に関する一連の競技であり、年間を通じて開催され、非常に競争が激しいと説明しました。 [(01:55:20)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=6920s)
- 全ての戦略のバックテストと統計の保存が完了した。[(01:56:47)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=7007s)
- Anthropic の API には、1 日あたりのレート制限がある。 [(02:20:05)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=8405s)
- Anthropic の CEO は、まるで誰かに借金をしているかのように、自社株を売却した。 [(02:23:46)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=8626s)
- あるユーザーが、アルゴリズム取引は非常に難しいとコメントし、Monarchというユーザーは、取引におけるアノマリーの見つけ方と、そのアノマリーが持続可能かどうかをどのように判断するかについて質問しました。[(02:25:08)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=8708s)
- 別のユーザーが、どの市場が定量取引に最適かについて質問し、暗号通貨と株式のどちらが良いかを尋ねました。これに対し、回答者は、どちらも最適ではないが、自分は暗号通貨に興味を持っているため、暗号通貨を好むと答えました。[(02:25:56)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=8756s)
- Renaissanceは毎日40テラバイトのデータをスクレイピングしているというコメントがあり、Monarchというユーザーは競争を恐れていると指摘されました。[(02:31:09)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=9069s)
- Jim Simons は、彼自身と彼の会社が公開されている株価データ (始値、高値、安値、終値、出来高) を使用していると述べています。 [(02:33:01)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=9181s)
- 話者は、マイクの設定を変更して、コーヒーをすする音を減らそうとしています。 [(02:36:12)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=9372s)
- 新しいノイズゲートは、-35 に設定されているクローズしきい値を調整するのに役立ちます。スライダーを右に動かしてゲートの感度を下げ、約 30 ～ 35 に設定してみてください。 [(02:42:59)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=9779s)
- ある人物（QuantまたはAlter Egoと呼ばれる）が動画投稿者を荒らしている。 [(02:53:51)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=10431s)
- ある人がSolanaで154,000ドルの損失を出しました。[10998]
- rsk は2013年に1BTCを100ドルから600ドルで購入しました。[(03:07:58)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11278s)
- 話者は Agent Zero に、Jim Simons 氏のトレーディング手法とアルゴリズム取引に焦点を当てた10,000字の論文を執筆するように指示した。 [(03:11:41)](https://www.youtube.com/watch?v=DUO6O_efLNc&t=11501s)