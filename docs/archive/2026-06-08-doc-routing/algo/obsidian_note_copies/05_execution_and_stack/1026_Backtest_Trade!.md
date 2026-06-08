

# QuantConnect/Lean: Lean Algorithmic Trading Engine by QuantConnect (Python, C#)
![](https://repository-images.githubusercontent.com/27251463/9268f080-61b0-11e9-9187-2a491d278e70)

https://www.lean.io/docs/v2/lean-cli

[Source URL](https://github.com/QuantConnect/Lean)

- LEANは、イベント駆動型のプロフェッショナル向けのアルゴリズムトレーディングプラットフォームであり、優雅なエンジニアリングと深い量的概念モデリングへの情熱で構築されています。ボックスアウトオブオルタナティブデータとライブトレーディングサポート。
- QuantConnect Lean CLIは、コマンドラインインターフェイスツールであり、QuantConnect Leanアルゴリズムトレーディングエンジンとやり取りするために使用されます。これは、複数の金融市場でアルゴリズムをバックテストおよびライブトレードするためのオープンソースプラットフォームです。
- QuantConnect Lean CLIを使用すると、開発者はプロジェクトを管理し、バックテストを実行し、ライブアルゴリズムを展開し、アルゴリズムトレーディングに関連するその他のタスクを実行できます。
- QuantConnect Lean CLIは、タスクの自動化、クラウドサービスとのシームレスな統合、QuantConnectコミュニティとのコラボレーションを可能にすることで、ワークフローを簡素化します。
- QuantConnect Lean CLIは、強力で柔軟なツールが必要な量的開発者向けに設計されています。
- QuantConnect Lean CLIをインストールするには、pip install leanを実行します。
- QuantConnect Lean CLIには、プロジェクトを作成する、Jupyter Lab環境を実行する、バックテストを実行する、最適化を実行する、ライブトレードを開始するなどのコマンドが用意されています。
- QuantConnect Lean CLIのフルコマンドリストは、LEAN CLIチートシートをダウンロードすることで参照できます。
- QuantConnect Lean CLIは、macOS、Linux（Debian、Ubuntu）、Windowsでインストールできます。
- QuantConnect Lean CLIには、Pythonサポートが含まれており、Pythonインストールプロセスの詳細はAlgorithm.Pythonプロジェクトで参照できます。
- QuantConnect Lean CLIは、ローカルクラウドハイブリッド開発をサポートしており、開発者は好みの開発環境でローカルに開発し、クラウドサービスとのシームレスな統合を実現できます。
- QuantConnect Lean CLIの問題や機能リクエストは、Leanリポジトリの問題として提出できます。
- QuantConnect Lean CLIのメーリングリストは、LEANフォーラムで見つけることができます。
- QuantConnect Lean CLIへの貢献は歓迎されており、貢献者は既存のコードを読み、貢献が既存のスタイルに合致するようにする必要があります。すべてのコード提出には、テストを伴う必要があります。
- QuantConnect Lean CLIは、オープンソースプロジェクトであり、多くの貢献者によってサポートされています。
- QuantConnect Lean CLIのオープンソース化は、Pioneersのサポートによって可能になりました。Pioneersは、QuantConnectの最初の100人の早期採用者で、プロジェクトをオープンソース化するために必要な資金を提供しました。


# Lean/Algorithm.Python at master · QuantConnect/Lean
![](https://repository-images.githubusercontent.com/27251463/9268f080-61b0-11e9-9187-2a491d278e70)


[Source URL](https://github.com/QuantConnect/Lean/tree/master/Algorithm.Python#quantconnect-python-algorithm-project)

- ローカル Python 自動補完機能を有効にするには、PyPI から quantconnect-stubs パッケージをインストールします。
 - `pip install quantconnect-stubs` コマンドを実行してインストールします。
 - `pip install --upgrade quantconnect-stubs` コマンドを実行して自動補完機能を最新バージョンに更新します。
 - 自動補完機能を有効にするには、プロジェクト ファイルの冒頭にインポート文を追加します。
- Lean をローカルで Python と共に設定するには、まず C# アルゴリズムを実行するための Lean のインストール手順に従います。
 - Python 3.8 をインストールします。
 - Windows の場合は、Python.org から Windows x86-64 MSI Python 3.8.13 インストーラーをダウンロードし、インストールします。Anaconda を使用する場合は、Anaconda 5.2 をインストールし、`conda install -y python=3.8.13` コマンドを実行して Python をアップグレードします。
 - macOS の場合は、Anaconda のドキュメント ページの「macOS へのインストール」の手順に従います。
 - Linux の場合は、miniconda を使用して Python をインストールします。
 - PYTHONNET_PYDLL 環境変数を設定します。
 - Windows の場合は、システムの環境変数に PYTHONNET_PYDLL を追加し、値を python.dll の場所に設定します。
 - macOS の場合は、`.bash-profile` ファイルに `export PYTHONNET_PYDLL="/{パス}/libpython3.8.dylib"` という行を追加します。
 - Linux の場合は、`/etc/environment` ファイルに `PYTHONNET_PYDLL="/{パス}/libpython3.8.so"` という行を追加します。
 - pandas と wrapt をインストールします。
 - `pip install pandas==1.4.3` コマンドを実行して pandas をインストールします。
 - `pip install wrapt==1.14.1` コマンドを実行して wrapt をインストールします。
- Python アルゴリズムを実行するには、config ファイルを更新し、`algorithm-type-name` を `BasicTemplateAlgorithm` に、`algorithm-language` を `Python` に、`algorithm-location` を `../../../Algorithm.Python/BasicTemplateAlgorithm.py` に設定します。
 - Lean をビルドし、実行します。
- Python.NET 開発 - Python.Runtime.dll のコンパイル
 - LEAN ユーザーは Python.Runtime.dll をコンパイルする必要はありません。この情報は、Python.Runtime.dll を改善したい開発者向けです。
 - QuantConnect/pythonnet の GitHub リポジトリをクローンするか、ZIP ファイルをダウンロードして展開します。
 - `msbuild pythonnet.sln /nologo /v:quiet /t:Clean;Rebuild` コマンドまたは `dotnet build pythonnet.sln` コマンドを実行して Python.Runtime.dll をコンパイルします。
- Python 自動補完インポート
 - `from AlgorithmImports import *` を Python ファイルの冒頭に追加して自動補完機能を有効にし、必要な型をインポートします。
-既知の問題
 - このドキュメントでは、既知の問題については説明していません。





# Lean/Data at master · QuantConnect/Lean
![](https://repository-images.githubusercontent.com/27251463/9268f080-61b0-11e9-9187-2a491d278e70)


[Source URL](https://github.com/QuantConnect/Lean/tree/master/Data)

- データは、特定のセキュリティに活動がない場合、その価格はファイルから省略されます。新しいティックと価格の変更のみが記録されます。
- データは、ティック、秒、分、時間、日単位の金融データと、フォレックス、オプション、先物、暗号通貨などのアセットタイプに分類されます。
- 各アセットタイプのデータフォーマットは、以下のリンクから参照できます。
 - 株式 | フォレックス | オプション | 先物 | 暗号通貨
- ティック、秒、分の金融データ: /data/securityType/marketName/resolution/ticker/date_tradeType.zip
- 時間、日単位の金融データ: /data/securityType/marketName/resolution/ticker.zip
- marketName値は、同じティッカーを持つ異なる取引可能なアセットを区別するために使用されます。たとえば、EURUSDは複数のブローカーで取引されており、それぞれの価格がわずかに異なります。
- TradeBar: TradeBarは、一定期間に集約されたアセットの取引ティックを表します。TradeBarファイルフォーマットは、高解像度（秒、分）と低解像度（日、時間）で若干異なります。
- QuoteBar: QuoteBarは、一定期間に集約されたトップオブブックの引用データ（ビッドとアスクバー）を表します。
- Tick: Tickデータは、アセットの個々の取引記録（「取引ティック」）または引用更新（「引用ティック」）を表します。Tickデータは即時であり、期間がありません。


![alt tag](https://raw.githubusercontent.com/QuantConnect/Lean/master/Documentation/logo.white.small.png) 
## LEAN Data Formats / Cryptocurrency (crypto)

QuantConnect hosts crypto data provided by [CryptoTick](https://www.cryptotick.com/).
The data contains both *Trade* and *Quote* data. Using the ToolBox applications `GDAXDownloader` and `BitfinexDownloader`, you can obtain historical *trade* data for free, but not *quote* data with this method. 
You can also download crypto data (trades and quotes starting with Tick and ending with Minute resolution) for a fee on our website. You can explore the data and purchase it at https://www.quantconnect.com/data/tree/crypto

CSV files are stored in compressed zip files, each containing a single CSV file.

Crypto data supports the following Resolutions:

* Tick
* Second
* Minute
* Hour
* Daily

The markets we currently support are: 

* GDAX/Coinbase Pro
* Bitfinex (Beta)

`tickType` in this documentation can refer to one of the following:

* trade
* quote

All times are in UTC unless noted otherwise.

### Minute and Second File Format
Second/Minute files are located in the crypto / market / resolution / symbol folder. 

The zip files have the filename: `YYYYMMDD_tickType.zip`. The CSV file contained within has the filename: `YYYYMMDD_symbol_resolution_tickType.csv`

Second/Minute trade format and example data is as follows:

| Time | Open | High | Low | Close | Volume |
| ---- | ---- | ---- | --- | ----- | ------ |
| 92000 | 132.01 | 132.05 | 131.95 | 132.03 | 49320 |

* Time - Milliseconds since midnight
* Open - Opening price
* High - High price
* Low - Low price
* Close - Closing price
* Volume - Total quantity trade 

Second/Minute quote format and example data is as follows:

| Time | Bid Open | Bid High | Bid Low | Bid Close | Last Bid Size | Ask Open | Ask High | Ask Low | Ask Close | Last Ask Size |
| ---- | -------- | -------- | ------- | --------- | ------------- | -------- | -------- | ------- | --------- | ------------- |
| 92000 | 132.01 | 132.05 | 132.00 | 132.03 | 24932.5 | 132.02 | 132.07 | 132.01 | 132.04 | 1200 |

* Time - Milliseconds since midnight
* Bid Open - Opening price for the best bid
* Bid High - Highest recorded bid price
* Bid Low - Lowest recorded bid price
* Bid Close - Closing price for the best bid
* Last Bid Size - Size of best bid at close
* Ask Open - Opening price for the best ask
* Ask High - Highest recorded ask price
* Ask Low - Lowest recorded ask price
* Ask Close - Closing price for the best ask
* Last Ask Size - Size of best ask at close

### Hour and Daily File Format
Hour/Daily files are located in the crypto / market / resolution folder. 

The zip files have the filename: `symbol_tickType.zip`. The CSV file contained within has the filename: `symbol.csv`

Hour/Daily trade format and example data is as follows:

| Time | Open | High | Low | Close | Volume |
| ---- | ---- | ---- | --- | ----- | ------ |
| 20180101 08:00 | 40.10 | 45.99 | 40.05 | 45.50 | 209342 |

* Time - Formatted as `YYYYMMDD HH:mm`
* Open - Opening price
* High - High price
* Low - Low price
* Close - Closing price
* Volume - Total quantity traded

Hour/Daily quote format and example data is as follows:

| Time | Bid Open | Bid High | Bid Low | Bid Close | Last Bid Size | Ask Open | Ask High | Ask Low | Ask Close | Last Ask Size |
| ---- | -------- | -------- | ------- | --------- | ------------- | -------- | -------- | ------- | --------- | ------------- |
| 20190224 00:00 | 10.10 | 10.12 | 10.10 | 10.11 | 209324.91 | 10.11 | 10.13 | 10.11 | 10.12 | 290253 |

* Time - Formatted as `YYYYMMDD HH:mm`
* Bid Open - Opening price for the best bid
* Bid High - Highest recorded bid price
* Bid Low - Lowest recorded bid price
* Bid Close - Closing price for the best bid
* Last Bid Size - Size of best bid at close
* Ask Open - Opening price for the best ask
* Ask High - Highest recorded ask price
* Ask Low - Lowest recorded ask price
* Ask Close - Closing price for the best ask
* Last Ask Size - Size of best ask at close

### Tick File Format
Ticks files are located in the data / crypto / market / tick folder. 

The zip files have the filename format: `YYYYMMDD_tickType.zip`. The CSV file contained within has the filename format: `YYYYMMDD_symbol_resolution_tickType.csv`

Tick trade format and example data is as follows:

| Time | Last Price | Quantity |
| ---- | ---------- | -------- |
| 86400 | 232.40 | 93.1 |

* Time - Milliseconds passed since midnight
* Last Price - Most recent trade price
* Quantity - Amount of asset purchased or sold

Tick quote format and example data is as follows:

| Time | Bid Price | Bid Size | Ask Price | Ask Size |
| ---- | --------- | -------- | --------- | -------- |
| 86400 | 232.40 | 20392.0 | 232.42 | 8059.5 |

* Time - Milliseconds passed since midnight
* Bid Price - Best bid price
* Bid Size - Best bid price's size/quantity
* Ask Price - Best ask price
* Ask Size - Best ask price's size/quantity

# Install .NET on Linux distributions - .NET
![](https://learn.microsoft.com/dotnet/media/dotnet-logo.png)


[Source URL](https://learn.microsoft.com/en-us/dotnet/core/install/linux)

- .NETは、さまざまなLinuxディストリビューションで利用可能です。
- .NETは、パッケージマネージャー、Snap、または手動でインストールできます。また、コンテナイメージとしても利用可能です。
- .NETは、公式のパッケージアーカイブやpackages.microsoft.comから入手できます。
- Microsoftからダウンロードした場合、.NETはMicrosoftによってサポートされます。その他の場所からダウンロードした場合、ベストエフォートサポートが提供されます。問題が発生した場合は、dotnet/coreで問題を報告できます。
- .NET SDKのSnapパッケージは、Canonicalによって提供および維持されています。Snapは、Linuxディストリビューションに組み込まれたパッケージマネージャーの代替手段です。
- .NETは、手動でインストールできますが、.NETの依存関係をインストールする必要がある場合があります。
- .NETはオープンソースプロジェクトです。フィードバックを提供するには、リンクを選択してください。
- .NETのインストール方法には、パッケージマネージャー、Snap、手動インストールがあります。
- .NETのサポート対象バージョンや、Debian、Ubuntu、RHEL、CentOS Streamへのインストール方法については、ドキュメントを参照してください。
- .NETのトラブルシューティング方法については、ドキュメントを参照してください。
- .NET SDKと.NET Runtimeのインストール方法については、ドキュメントを参照してください。
- .NETのSnapパッケージのインストール方法については、ドキュメントを参照してください。
- Ubuntuへのインストール方法については、ドキュメントを参照してください。
- RHELとCentOS Streamへのインストール方法については、ドキュメントを参照してください。


# .NET and Ubuntu overview - .NET
![](https://learn.microsoft.com/dotnet/media/dotnet-logo.png)


[Source URL](https://learn.microsoft.com/en-us/dotnet/core/install/linux-ubuntu)

## .NETをUbuntuにインストールする方法
- NETをUbuntuにインストールする方法について説明します。Ubuntu 22.04以降のバージョンでは、ほとんどのサポートされている.NETバージョンが、組み込みのUbuntuフィードに含まれています。
- Ubuntu .NETバックポートパッケージリポジトリには、組み込みのUbuntuパッケージフィードに含まれないサポートされている.NETバージョンが含まれています。詳細については、「サポートされているディストリビューション」セクションを参照してください。
- Ubuntu 23.10以前のバージョンでは、Microsoftパッケージリポジトリには、現在サポートされている、または過去にサポートされていたすべての.NETバージョンが含まれています。
- NETパッケージは、UbuntuまたはMicrosoftのフィードからのみ取得することをお勧めします。複数のパッケージリポジトリから.NETパッケージを混在させることは、問題を引き起こす可能性があるため、避ける必要があります。

## .NETのインストール方法
- NETをインストールする方法には、パッケージマネージャー（組み込みUbuntuフィード、.NETバックポートUbuntuフィード、Microsoftフィード）とスクリプト/手動抽出の2種類があります。
- パッケージマネージャー（組み込みUbuntuフィード）は、通常、最新バージョンが利用可能であり、パッチがすぐに利用可能であり、依存関係が含まれており、削除が簡単です。ただし、Ubuntu 16.04、18.04、20.04では利用できないため、.NETバージョンはUbuntuバージョンによって異なります。
- パッケージマネージャー（.NETバックポートUbuntuフィード）は、組み込みのUbuntuフィードに含まれないサポートされている.NETバージョンを含んでいます。パッチがすぐに利用可能であり、依存関係が含まれており、削除が簡単です。ただし、Ubuntu 16.04、18.04、20.04では利用できず、Ubuntu .NETバックポートパッケージリポジトリの登録が必要です。
- パッケージマネージャー（Microsoftフィード）は、サポートされているバージョンが常に利用可能であり、パッチがすぐに利用可能であり、依存関係が含まれており、削除が簡単です。ただし、Ubuntu 24.04以降では利用できず、Microsoftパッケージリポジトリの登録が必要です。
- スクリプト/手動抽出では、.NETのインストール場所を制御できます。プレビューリリースが利用可能であり、更新プログラムと依存関係を手動でインストールする必要があります。

## .NETインストール方法の決定
- NETをインストールする方法を決定するには、Ubuntuのバージョンと必要な.NETバージョンを考慮する必要があります。Ubuntu 22.04以降のバージョンでは、組み込みのUbuntuフィードから.NETをインストールすることをお勧めします。
- Ubuntuのバージョンが必要な.NETのバージョンを提供している場合は、Ubuntuのフィードからインストールすることをお勧めします。
- Ubuntuのバージョンが必要な.NETのバージョンを提供していない場合は、Microsoftのパッケージリポジトリを登録し、そこから.NETをインストールすることをお勧めします。
- 必要な.NETのバージョンが利用できない場合は、dotnet-installスクリプトを使用することをお勧めします。
- プレビュー版をインストールする場合は、APTを使用せずに、Linuxインストールスクリプトまたはtarballを使用してインストールすることができます。

## 特定のアーキテクチャ向けの.NETのインストール
- ArmベースのCPUを使用している場合は、Ubuntuのバージョンが必要な.NETのバージョンを提供している場合は、Ubuntuのフィードからインストールすることをお勧めします。
- IBM System Zプラットフォームを使用している場合は、.NET 8以降のバージョンをUbuntu 24.04以降でサポートしています。

## サポートされているディストリビューションと.NETのサポート期間
- サポートされている.NETのリリースとUbuntuのバージョンの一覧は、Supported distributionsセクションに記載されています。
- Ubuntuのバージョンがサポート期間を終了すると、.NETもサポートされなくなります。

## .NETバックポートパッケージリポジトリ
- NETバックポートパッケージリポジトリは、Ubuntuのフィードに含まれない.NETのバージョンを提供します。
- NETバックポートパッケージリポジトリを登録するには、sudo add-apt-repository ppa:dotnet/backportsコマンドを実行します。
- NETバックポートパッケージリポジトリを登録解除するには、sudo add-apt-repository --remove ppa:dotnet/backportsコマンドを実行します。

## パッケージリポジトリの登録
- NETをインストールする前に、`add-apt-repository`コマンドが見つからないエラーが発生した場合は、`software-properties-common`パッケージをインストールする必要があります。これは、ターミナルで`sudo apt update`および`sudo apt install software-properties-common`コマンドを実行することで実行できます。
- Microsoftパッケージリポジトリを登録するには、ターミナルで`source /etc/os-release`、`wget https://packages.microsoft.com/config/$ID/$VERSION_ID/packages-microsoft-prod.deb -O packages-microsoft-prod.deb`、`sudo dpkg -i packages-microsoft-prod.deb`、`rm packages-microsoft-prod.deb`、`sudo apt update`コマンドを実行します。
- Microsoftパッケージリポジトリは、x64アーキテクチャのみをサポートします。その他のアーキテクチャ（Armなど）は、インストーラースクリプトまたは手動インストールを使用して.NETをインストールする必要があります。
- プレビュー版は、Microsoftパッケージリポジトリに含まれていません。

## .NETのインストール
- NETをインストールするには、ターミナルで`sudo apt install <パッケージ名>`コマンドを実行します。パッケージ名は、インストールしたい.NETパッケージの名前を指定します。
- サポートされている.NETパッケージの一覧は、以下の通りです。
- ASP.NET Core Runtime 8.0: aspnetcore-runtime-8.0
- NET Runtime 8.0: dotnet-runtime-8.0
- NET SDK 8.0: dotnet-sdk-8.0
- ASP.NET Core Runtime 6.0: aspnetcore-runtime-6.0
- NET Runtime 6.0: dotnet-runtime-6.0
- NET SDK 6.0: dotnet-sdk-6.0

## .NETのアンインストール
- NETをアンインストールするには、ターミナルで`sudo apt-get remove <パッケージ名>`コマンドを実行します。
- NETのプレビュー版とリリース候補版は、パッケージマネージャーを使用してインストールできますが、以前にプレビュー版をインストールした場合、コンフリクトが発生する可能性があります。プレビュー版をアンインストールすることで、この問題を解決できます。
- プレビュー版をアンインストールする方法については、「.NETランタイムとSDKのアンインストール方法」を参照してください。

## .NETのアップグレード
- パッケージマネージャーを使用してインストールした場合、apt upgradeコマンドを使用してパッケージをアップグレードできます。たとえば、dotnet-sdk-8.0パッケージをアップグレードするには、次のコマンドを実行します。
- Ubuntu 22.04以降のバージョンでは、.NETの一部しかインストールされていない場合があります。この問題は、2つの異なるパッケージソースを使用していることが原因である可能性があります。詳細については、「Linuxで発生する.NETエラーのトラブルシューティング」を参照してください。

## APTを使用した.NETのインストールに関するトラブルシューティング
- APTを使用して.NETをインストールする際に発生する一般的なエラーについては、以下の情報を参照してください。
- パッケージが見つからない場合：Microsoftのパッケージフィードはx64アーキテクチャのみをサポートしているため、Armなどの他のアーキテクチャではサポートされません。
- パッケージが見つからない場合や、一部のパッケージをインストールできない場合：次のコマンドを実行してパッケージリストを更新し、再度インストールを試みてください。
- 上記のコマンドが機能しない場合、手動でインストールすることもできます。Ubuntu 23.10以降のバージョンの場合、次のコマンドを実行してください。
- Ubuntu 23.10以前のバージョンの場合、次のコマンドを実行してください。
- パッケージのダウンロードに失敗した場合、エラー メッセージ「Failed to fetch ... File has unexpected size ... Mirror sync in progress?」が表示されることがあります。このエラーは、.NETのパッケージフィードがアップグレード中であることを示しており、後で再度試してください。アップグレード中、パッケージフィードは30分以内に利用可能になるはずです。

## .NETに必要な依存関係
- NETアプリケーションを実行するために必要な依存ライブラリには、ca-certificates、libc6、libgcc1（16.xおよび18.x用）、libgcc-s1（20.x以降用）、libgssapi-krb5-2、libicu55（16.x用）、libicu60（18.x用）、libicu66（20.x用）、libicu70（22.04用）、libicu72（23.10用）、libicu74（24.04以降用）、liblttng-ust1（22.x以降用）、libssl1.0.0（16.x用）、libssl1.1（18.xおよび20.x用）、libssl3（22.x以降用）、libstdc++6、libunwind8（22.x以降用）、zlib1gなどがあります。
- これらの依存ライブラリは、apt installコマンドを使用してインストールできます。たとえば、zlib1gライブラリをインストールするには、sudo apt install zlib1gというコマンドを実行します。
- NETアプリケーションがSystem.Drawing.Commonアセンブリを使用する場合、libgdiplusもインストールする必要があります。ただし、System.Drawing.CommonはLinuxではサポートされていないため、これは.NET 6でのみ動作し、System.Drawing.EnableUnixSupportランタイム構成スイッチを設定する必要があります。libgdiplusの最新バージョンをインストールするには、Monoリポジトリをシステムに追加する必要があります。
- 依存ライブラリを手動でインストールする必要があるのは、パッケージマネージャーを使用せずに.NETをインストールした場合、またはセルフコンタインドアプリを公開した場合のみです。


# Install .NET Runtime on Linux with Snap - .NET
![](https://learn.microsoft.com/dotnet/media/dotnet-logo.png)


[Source URL](https://learn.microsoft.com/en-us/dotnet/core/install/linux-snap-runtime)

- .NET Runtime を Snap でインストールする方法について説明します。.NET Runtime の Snap パッケージは、Canonical によって提供および維持されています。Snap は、Linux ディストリビューションに組み込まれたパッケージ マネージャーの代替手段として役立ちます。
- Snap は、アプリケーションとその依存関係をバンドルしたもので、多くの Linux ディストリビューションで動作します。Snap は、Snap Store から検索およびインストールできます。Snap の詳細については、Quickstart tour を参照してください。
- .NET ツールを使用する場合は、dotnet-install スクリプトまたは Linux ディストリビューションのパッケージ マネージャーを使用して .NET をインストールすることをお勧めします。
- 以下の条件が必要です。
 - Snap をサポートする Linux ディストリビューション
 - snapd (Snap デーモン)
 - Linux ディストリビューションにはすでに Snap が含まれている場合があります。ターミナルから snap コマンドを実行して、コマンドが動作するかどうかを確認してください。サポートされている Linux ディストリビューションの一覧と、Snap をインストールする方法については、Installing snapd を参照してください。
- .NET のリリース
 - マイクロソフトは、.NET を Long Term Support (LTS) と Standard Term Support (STS) の 2 つのサポート ポリシーで公開しています。すべてのリリースの品質は同じですが、サポート期間が異なります。LTS リリースは 3 年間、STS リリースは 18 か月間の無料サポートとパッチを受け取ります。詳細については、.NET Support Policy を参照してください。
 - 現在、マイクロソフトによってサポートされている .NET のバージョンは以下のとおりです。
 - 8.0 (LTS) - サポート終了日: 2026 年 11 月 10 日
 - 6.0 (LTS) - サポート終了日: 2024 年 11 月 12 日
- .NET Runtime のインストール
 - .NET 8 Runtime Snap パッケージをインストールするには、以下の手順に従います。
 - 各 .NET Runtime は、個別の Snap パッケージとして公開されています。以下の表にパッケージの一覧を示します。
- dotnet コマンドの有効化
 - .NET Runtime Snap パッケージをインストールした後、dotnet コマンドは自動的に構成されません。`sudo snap alias dotnet-runtime-80.dotnet dotnet` コマンドを使用して、dotnet コマンドをターミナルから使用します。
- インストール場所のエクスポート
 - DOTNET_ROOT 環境変数は、ツールによって .NET がインストールされている場所を決定するために使用されます。Snap を使用して .NET をインストールした場合、この環境変数は構成されません。プロファイルに DOTNET_ROOT 環境変数を構成する必要があります。Snap のパスは、以下の形式で使用されます: `/snap/{パッケージ}/current`。たとえば、dotnet-runtime-80 Snap をインストールした場合、`export DOTNET_ROOT=/snap/dotnet-runtime-80/current` コマンドを使用して、環境変数を .NET のインストール場所に設定します。
- 環境変数の永続化
 - 前述の export コマンドは、環境変数をターミナル セッションにのみ設定します。シェル プロファイルを編集して、コマンドを永続化する必要があります。シェル プロファイルの場所は、シェルによって異なります。たとえば、Bash シェルでは、`~/.bash_profile` または `~/.bashrc` ファイルを編集します。Z Shell の場合は、`~/.zshrc` または `~/.zprofile` ファイルを編集します。
- トラブルシューティング
 - dotnet ターミナル コマンドが動作しない場合
 - Snap パッケージは、パッケージによって提供されるコマンドにエイリアスを設定できます。.NET Runtime Snap パッケージは、dotnet コマンドを自動的にエイリアス設定しません。dotnet コマンドを Snap パッケージにエイリアス設定するには、`sudo snap alias dotnet-runtime-80.dotnet dotnet` コマンドを使用します。dotnet-runtime-80 を実際のランタイム パッケージ名に置き換えます。
 - WSL2 で Snap をインストールできない場合
 - systemd が WSL2 インスタンスに有効になっている必要があります。`/etc/wsl.conf` ファイルをテキスト エディターで開き、以下の構成を貼り付けます: `[boot] systemd = true` ファイルを保存し、WSL2 インスタンスを PowerShell で再起動します。`wsl.exe --shutdown` コマンドを使用します。
- .NET CLI の使用
 - ターミナルを開き、`dotnet` コマンドを実行します。.NET CLI の使用方法については、.NET CLI overview を参照してください。


# Install .NET SDK on Linux with Snap - .NET
![](https://learn.microsoft.com/dotnet/media/dotnet-logo.png)


[Source URL](https://learn.microsoft.com/en-us/dotnet/core/install/linux-snap-sdk)

## .NET SDKをSnapでインストールする方法
- NET SDKをSnapでインストールする方法について説明します。.NET SDKのSnapパッケージは、Canonicalによって提供および維持されています。Snapは、Linuxディストリビューションに組み込まれたパッケージマネージャーの代替手段です。Snapは、アプリケーションとその依存関係のバンドルであり、多くのLinuxディストリビューションで動作します。Snapは、Snap Storeから検索およびインストールできます。
- NET SDKのSnapパッケージをインストールするには、LinuxディストリビューションがSnapをサポートしている必要があります。また、snapd（Snapデーモン）がインストールされている必要があります。snapコマンドが動作するかどうかを確認するには、ターミナルからsnapコマンドを実行してください。
- Microsoftは、.NETを2つのサポートポリシー、Long Term Support（LTS）とStandard Term Support（STS）で公開しています。すべてのリリースの品質は同じですが、サポート期間が異なります。LTSリリースは3年間、STSリリースは18ヶ月間の無料サポートとパッチが提供されます。
- NET SDKのSnapパッケージはすべて、dotnet-sdkという同じ識別子で公開されています。特定のバージョンのSDKをインストールするには、チャネルを指定する必要があります。SDKには、ASP.NET Coreと.NETランタイムが含まれます。

## .NET SDKのSnapパッケージのインストール
- NET SDKのSnapパッケージをインストールするには、ターミナルを開き、snap installコマンドを使用します。たとえば、最新の安定版チャネルをインストールするには、sudo snap install dotnet-sdk --classicコマンドを実行します。
- NET SDKのバージョンとSnapパッケージのチャネルは以下の通りです。
- （LTS）：8.0/stable、latest/stable、lts/stable
- ：7.0/stable（サポート終了）
- （LTS）：6.0/stable
- ：5.0/stable（サポート終了）
- ：3.1/stable（サポート終了）
- ：2.1/stable（サポート終了）

## .NET SDKのインストール後の設定
- NET SDKをインストールした後、DOTNET_ROOT環境変数を設定する必要があります。DOTNET_ROOT環境変数は、ツールが.NETのインストール場所を決定するために使用されます。.NET SDKのSnapパッケージをインストールすると、DOTNET_ROOT環境変数は自動的に設定されません。したがって、プロファイルにDOTNET_ROOT環境変数を設定する必要があります。

## .NET CLIの使用方法
- NET CLIを使用するには、ターミナルを開いて「dotnet」と入力します。
- 「dotnet」コマンドを実行すると、使用方法やオプションが表示されます。オプションには、ヘルプの表示、.NET情報の表示、インストールされたSDKやランタイムの一覧表示などがあります。
- 「dotnet」コマンドが機能しない場合、Snapパッケージが提供するコマンドにエイリアスを設定する必要があります。エイリアスが作成されていない場合は、「sudo snap alias dotnet-sdk.dotnet dotnet」コマンドを使用してエイリアスを設定します。

## WSL2でのSnapのインストール
- WSL2でSnapをインストールできない場合、systemdを有効にする必要があります。「/etc/wsl.conf」ファイルに「[boot] systemd = true」を追加し、PowerShellでWSL2インスタンスを再起動します。

## その他の問題の解決策
- 他のアプリケーションが.NET SDKを解決できない場合、DOTNET_ROOT環境変数を永続的にエクスポートするか、Snapのdotnet実行ファイルをプログラムが探している場所にシンボリックリンクします。
- TLS/SSL証明書エラーが発生する場合、環境変数「SSL_CERT_FILE」と「SSL_CERT_DIR」を設定します。証明書の場所はディストリビューションによって異なります。例えば、Fedoraでは「/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem」です。