

# wukan1986/polars_ta: Technical Analysis Indicators for polars
![](https://opengraph.githubassets.com/060251bc06838f7a5a8ca953221d30829815ac56252f9b4ff55d3d887a2dd8ae/wukan1986/polars_ta)


[Source URL](https://github.com/wukan1986/polars_ta/tree/main)

## インストール
- このプロジェクトは、polars用のテクニカル分析インジケーターのラッパーを提供します。
- インストール方法は、pipを使用する方法とソースコードからビルドする方法の2通りあります。
- pipを使用する場合、コマンドは`pip install -i https://pypi.org/simple --upgrade polars_ta`です。中国のミラーを使用する場合は、`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade polars_ta`です。
- ソースコードからビルドする場合、GitHubからリポジトリをクローンし、`python -m build`を実行してwhlファイルを作成し、`pip install`でインストールします。

## TA-Libのインストール
- TA-Libをインストールするには、非公式のTA-Libのホイールをダウンロードする必要があります。

## 使い方
- 使い方は、examplesフォルダーのサンプルコードを参照してください。
- このプロジェクトでは、polarsのExprを使用して計算を行うため、Seriesを使用していません。
- 関数はクラスのメソッドではなく、独立した関数として実装されています。
- wq、ta、tdxの3つの名前空間があり、それぞれWorldQuant Alpha、TA-Lib、TDXのラッパーを提供しています。
- wqはWorldQuant Alphaを模倣しており、taはTA-Libのpolars版であり、tdxはTDXのラッパーです。
- これらの名前空間は、Exprに近い実装を提供するように設計されています。
- また、Null/NaN値の処理についても説明されています。

## Expr.map_batchesの使用
- このプロジェクトは、Expr.map_batchesを使用して第三者ライブラリを呼び出すことができますが、入力と出力のフォーマット要件に応じてラッパー関数を使用する必要があります。
- さらに、register_expr_namespaceを使用してコードを簡略化する方法も提供されています。
- つの実装方法、helper.pyとwrapper.pyがあり、それぞれのProsとConsが説明されています。

## polars_taの概要
- polars_taは、Polarsをベースにしたオペレーター ライブラリです。量化投研でよく使われる技術指標やデータ処理関数を実装しています。TA-LibなどのExprに変換しにくいライブラリも関数呼び出しをラップしています。

## polars_taのインストール
- polars_taのインストール方法には、pipを使用したオンラインインストールと、ソースコードからインストールする方法があります。Windowsユーザーは、必要なwhlファイルをダウンロードしてインストールすることもできます。

## polars_taの使用法
- polars_taの使用方法は、examplesディレクトリを参照することで確認できます。たとえば、expr_codegenで使用するには、ts_などのプレフィックスが必要です。

## polars_taの設計原則
- polars_taの設計原則は、メンバー関数を独立関数に変更し、入出力にExprを使用することです。wq公式を優先的に実装し、TA-LibのPolars版を実装することも行っています。

## polars_taの第三方ライブラリ呼び出し
- polars_taには、Expr.map_batchesを使用して第三方ライブラリを呼び出す機能がありますが、入出力形式に制限があるため、関数でラップする必要があります。

## polars_taのコード自動生成
- polars_taには、コード自动生成の機能があり、codegen_talib2.pyを使用して__init__.pyを生成できます。この方法は、遺伝的アルゴリズムへの入力とIDEのインテリセンスを両立できます。

## polars_taの開発とデバッグ
- polars_taの開発とデバッグには、GitHubからソースコードをクローンし、pip install -e .を実行する必要があります。新しい関数を追加した場合は、prefix_ta.pyまたはprefix_tdx.pyを実行してプレフィックスファイルを生成する必要があります。



# wukan1986/AlphaInspect: factor performance visualization
![](https://opengraph.githubassets.com/dd474a35d54fc9fa3bbbe370d6e373c116153e2ac3bbebf29601c0b244dc0399/wukan1986/AlphaInspect)


[Source URL](https://github.com/wukan1986/AlphaInspect)

- AlphaInspectは、AlphaLensに似た単一因子分析ツールです。
- AlphaInspectをインストールするには、pip install -i https://pypi.org/simple --upgrade alphainspectを実行します。中国国内の場合、pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade alphainspectを実行します。
- AlphaInspectを使用するには、データを準備する必要があります。data/prepare_data.pyを実行して、データを準備します。
- データには、date、asset、factor、forward returnなどのフィールドが必要です。factorは因子値、forward returnは遠期収益率です。
- forward returnは、収益率を計算した後、開始位置に戻す必要があります。収益率はshift(-n)で計算されますが、因子はshift(n)で計算されません。
- これは、因子が多数ある場合、すべての因子を移動する必要があり、作業量が非常に大きくなるためです。一方、収益率は少ないため、移動する必要がありません。
- AlphaInspectは、expr_codegenやpolars_taなどのプロジェクトを使用することを推奨しています。
- AlphaInspectを使用するには、examples/demo1.py、examples/demo2.py、examples/demo3.py、examples/demo4.pyなどのサンプルコードを実行する必要があります。
- これらのサンプルコードは、簡易なグラフや詳細なグラフ、HTMLレポート、イベントグラフなどを出力します。
- AlphaInspectは、forward_returnsを自動的に計算しません。代わりに、ユーザーは外部でforward_returnsを生成し、AlphaInspectに渡す必要があります。
- AlphaInspectは、去極値、標準化、業界中性化などの操作を実行しません。これらの操作は、ユーザーが外部で実行する必要があります。
- AlphaInspectは、資金配分に等権重みのみを使用します。AlphaLensは、因子加重や多空設定などをサポートしています。
- AlphaInspectは、収益率計算方法がAlphaLensと異なります。AlphaInspectは、ユーザーが提供した1期収益率を使用し、要求に応じて持続または調整を実行して、新しい権益を計算します。
- AlphaInspectは、データの組織方式がAlphaLensと同じです。両方とも長表形式で、因子は移動せず、収益率は計算後に因子生成時刻に戻されます。
- AlphaInspectは、滑点や手数料を考慮しません。これは、単一因子分析は多因子分析の合成に使用されるため、手数料や滑点によって部分的な単一因子を欠損することは避けられるべきだからです。
- AlphaInspectは、収益計算の精度を求めません。収益計算は、因子のパフォーマンスを評価するためにのみ使用されます。
- AlphaInspectのソースコードは、git --clone https://github.com/wukan1986/alphainspect.gitを実行して取得できます。


# AlphaInspect/cum_returns.md at main · wukan1986/AlphaInspect
![](https://opengraph.githubassets.com/dd474a35d54fc9fa3bbbe370d6e373c116153e2ac3bbebf29601c0b244dc0399/wukan1986/AlphaInspect)


[Source URL](https://github.com/wukan1986/AlphaInspect/blob/main/cum_returns.md)

- AlphaInspectプロジェクトでは、累積収益率の計算方法が検討されている。
- 多頭計算は正しく行われているが、空頭計算は失敗していることが分かった。
- 例えば、価格が1 -> 1.5 -> 2に変化した場合、収益率は0.5 -> 0.3333となるが、空頭収益は1 -> 0.5 -> 0.333となる。
- 正しい計算方法は、開倉現金流を考慮することである。
- 例えば、価格が1 -> 1.5 -> 2に変化した場合、多頭持倉市値は1 -> 1.5 -> 2、開倉現金流は-1 -> -1 -> -1、利益は0 -> 0.5 -> 1となる。
- 空頭の場合も同様に計算することができる。
- ただし、収益率の計算方法は単利に変更された。
- これは、分層収益計算の目的は因子の単調性を考察することであり、精度は重要ではないためである。
- また、LightBTプロジェクトを使用することで、より精確な収益曲線を取得することができる。
- AlphaInspectプロジェクトでは、多頭と空頭の収益率を計算する際に、資金の再平衡問題を考慮していない。
- これは、資金の再平衡問題を考慮することで、より精確な収益曲線を取得することができる。
- ただし、AlphaInspectプロジェクトでは、資金の再平衡問題を考慮することで、計算時間が増加するため、単利に変更された。


# wukan1986/expr_codegen: codegen from expression to others, such as polars, pandas
![](https://opengraph.githubassets.com/31d00c73bd861ed2f76bf2050aa5bca54ac94d3942a9d046953c7cbbe0c5a3bf/wukan1986/expr_codegen)


[Source URL](https://github.com/wukan1986/expr_codegen)

## expr_codegen について
- expr_codegen は、DSL（Domain Specific Language）であり、polars_ta などのライブラリで使用される式をコードに変換するツールです。
- このツールは、polars_ta で簡単に特徴計算式を書くことができるように設計されており、時系列と截面の式を混用する場合に自動的にグループ化して計算を効率化することができます。
- また、Common Subexpression Elimination（CSE）を使用して、式を簡略化し、計算を高速化することができます。
- このプロジェクトは、polars_ta との依存関係が強いですが、他のライブラリ（pandas、cudf.pandas）にも対応する予定です。

## 使用方法
- 初級ユーザーは、https://exprcodegen.streamlit.app にアクセスして、式をコードに変換することができます。
- このツールは、sympy プロジェクトに依存しており、simplify、cse、StrPrinter などの関数を使用しています。
- また、式をグループ化するために、get_current、get_children、extract などの関数を使用しています。
- さらに、DAG（有向無環グラフ）を使用して、式を分層化し、コードを生成しています。

## サンプルコード
- このプロジェクトには、demo_express.py、demo_exec_pl.py、demo_transformer.py などのサンプルコードが含まれています。
- また、printer.py には、式をコードに変換するための関数が定義されています。

## インストール方法
- このプロジェクトは、Python 3.x で動作し、pip を使用してインストールすることができます。
- 依存関係には、sympy、polars、pandas、cudf.pandas などが含まれています。

## 使用目的
- このプロジェクトは、Alpha101 などのアルゴリズムトレーディングプロジェクトで使用することを目的としています。
- また、式をコードに変換する際には、_ 开头の変数は自動的に削除され、_x_ 开头の変数は中間変数として使用されます。
- さらに、式をコードに変換する際には、if_else 関数を使用して、三元演算子を代替することができます。