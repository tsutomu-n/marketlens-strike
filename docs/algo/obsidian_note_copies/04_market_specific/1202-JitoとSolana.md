
# Jito Bundles [Solana Tutorial] - Oct 7th '23
![](https://i.ytimg.com/vi/HZ1pK9i6zx4/maxresdefault.jpg)



## JitoとSolanaのトランザクションバンドル
- Jitoは、Solanaのトランザクションバンドルを提供するプロジェクトであり、トランザクションのバンドル化により、複数のトランザクションを1つの単位として処理できるようになる [(00:00:05)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=5s)。
- Solanaのトランザクションは原子性を持ち、トランザクション内のすべての命令が成功するか、すべて失敗するかのいずれかであるが、トランザクションレベルではこの原子性を実現することはできない [(00:01:04)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=64s)。
- ただし、バンドルを使用することで、複数のトランザクションを1つの単位として処理し、原子性を実現できるようになる [(00:01:59)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=119s)。
- バンドルは、バリデーター側で処理されるため、バリデーターがトランザクションをグループ化し、すべてのトランザクションが成功するか、すべて失敗するかを判断できる [(00:02:10)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=130s)。
- Jitoは、バリデーター用のソフトウェアを提供しており、バンドルを使用したトランザクション処理を可能にする [(00:03:47)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=227s)。
- Jitoのバリデーターは、Solana Labsのバリデータークライアントに追加のコードを組み込んだものであり、バンドルを使用したトランザクション処理を可能にする [(00:04:00)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=240s)。
- 現在、約3分の1のステークウェイトがJitoのバリデーターに集中しており、約3分の1のブロックがJitoのバリデーターによって生成されている [(00:04:11)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=251s)。
- G2バリデータは、トランザクションをバンドルとして処理することができ、バンドル内のすべてのトランザクションが成功する場合にのみ、ブロックに含めることができる [(00:04:17)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=257s)。
- バリデータは、バンドル内のトランザクションが失敗した場合、ブロックスペースを無駄にしないために、バンドル内のトランザクションをブロックに含めない [(00:04:33)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=273s)。
- バリデータがバンドルを処理する理由は、バンドル内のトランザクションに追加のチップ（tip）が含まれているためであり、これはバリデータが提供するサービスに対する報酬となる [(00:04:52)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=292s)。
- バンドルには、複数のトランザクションを含めることができ、バンドル内のすべてのトランザクションが成功する場合にのみ、ブロックに含めることができる [(00:05:24)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=324s)。
- バンドルを使用することで、ArbitrageやLiquidationなどの高度な取引戦略を実行することができる [(00:05:30)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=330s)。

## Searcherとバンドルの作成
- バンドルは、Searcherと呼ばれるエンティティによって作成され、バリデータに送信される [(00:08:08)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=488s)。
- Searcherは、バンドル内のトランザクションを分析し、ArbitrageやLiquidationなどの取引戦略を実行することができる [(00:08:17)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=497s)。
- バンドルは、GTO（Generalized Transaction Output）というプロトコルによって実現されており、バリデータとSearcherの間でトランザクションを調整するためのブロックエンジンを使用する [(00:07:51)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=471s)。
- バンドルは、Solanaブロックチェーン上で実行される [(00:06:15)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=375s)。

## ブロックエンジンとバリデータの役割
- トランザクションをバンドルにまとめてブロックエンジンに送信し、バリデータに転送される仕組みについて説明している [(00:08:20)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=500s)。
- バリデータは投票トランザクションのみを直接受け取り、ブロックエンジンはバンドルをバリデータに転送する [(00:08:27)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=507s)。
- ブロックエンジンはバリデータに送信するバンドルを選択し、バリデータはブロックを構築する [(00:08:47)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=527s)。
- サーチャーは誰でも実行でき、バリデータも同様であるが、サーチャーはバンドルを送信する役割を担う [(00:09:13)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=553s)。
- バンドルを送信する際、次のリーダーに接続する必要はなく、ブロックエンジンに接続するだけでよい [(00:09:43)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=583s)。

## G2バンドルの利点とユースケース
- G2バンドルはトランザクションの順次実行を可能にする [(00:10:52)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=652s)。
- G2バンドルを使用すると、トランザクションの順序を指定でき、同じスロット内で実行順序を保証できる [(00:11:30)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=690s)。
- G2バンドルは、DeFiオペレーター、NFT関係者など、順次トランザクション実行が必要なユーザーに有用である [(00:11:45)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=705s)。
- NFTのバーンや新しいNFTの作成など、複数のトランザクションが必要な場合にG2バンドルが有効である [(00:11:59)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=719s)。

## Jito Bundlesの使い方
- Jito Bundlesを使用することで、Solana上でAtomicなトランザクションを実行することができる [(00:12:25)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=745s)
- Jito Bundlesは、トランザクションの順序を保証し、すべてのトランザクションが成功するか、すべて失敗するかのどちらかになる [(00:12:38)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=758s)
- Jito Bundlesを使用するには、ローカルのKeypair、Block Engine URL、Block Engine APIキーが必要 [(00:12:47)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=767s)
- Block Engine URLは、GTO Labsが提供するものを使用することができる [(00:12:59)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=779s)
- Block Engine APIキーは、GTO Labsのフォームを提出することで取得できる [(00:13:41)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=821s)
- Jito Bundlesを使用するには、On-chainアドレス（Tipアドレス）が必要 [(00:13:59)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=839s)
- Tipアドレスは、Tip Payment Programによって運営されており、複数のアドレスがある [(00:14:05)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=845s)
- 複数のTipアドレスがある理由は、ボトルネックを避けるため [(00:14:18)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=858s)
- Jito Bundlesは、SolanaのMainnetとTestnetの両方で動作する [(00:14:29)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=869s)
- Jito Bundlesを使用するには、カスタムRPCを使用することもできる [(00:15:03)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=903s)
- Jito Bundlesは、順序付きのトランザクションリストを実行することができる [(00:15:40)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=940s)
- Jito Bundlesは、トランザクションが成功するか、すべて失敗するかのどちらかになる [(00:15:47)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=947s)
- Jito Bundlesは、スロット境界を越えないように実行される [(00:16:02)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=962s)
- Jito Bundlesは、すべてのトランザクションが成功した場合にのみ、On-chainにコミットされる [(00:16:11)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=971s)

## Jitoバンドルの詳細と使用例
- Jitoバンドルとは、複数のトランザクションをバンドルにまとめて送信し、順番に実行されるようにする機能である。バンドルを使用すると、トランザクションがすべて実行されることを保証できる [(00:16:52)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1012s)。
- Jitoバンドルは、Cheetoバリデータクライアントのバンドル実行ステージで実行される。バンドル実行ステージは、バンドル内のトランザクションを順番に実行する [(00:17:04)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1024s)。
- バンドルを使用するには、Jito Solanaリーダーがブロックを生成している必要がある。Jitoクライアントは、バンドルをブロックエンジンに送信し、バリデータに送信される [(00:17:37)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1057s)。
- バンドルは、約3分の1のスロットで使用できる。Jitoクライアントは、バンドルをブロックエンジンに送信し、バリデータに送信される [(00:18:00)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1080s)。
- バンドルの使用例としては、ArbitrageやDeFi操作のバッチ処理がある。Arbitrageでは、Oracleの更新後にすぐにliquidationトランザクションを送信することができる [(00:18:11)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1091s)。
- バンドルを送信するには、APIゲートを使用する必要がある。現在、バンドルを送信することは無料であるが、最低でも1,000 LamportのTipを設定する必要がある [(00:19:07)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1147s)。
- Tipを設定するには、s_transferトランザクションを送信し、TipアドレスにLamportを送信する必要がある。Tipは、バンドルの最後のトランザクションに含める必要がある [(00:19:42)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1182s)。
- Jitoバンドル内の最後のトランザクションに注目する必要がある。GTOバリデーターにチップを渡すと、優先順位料金を追加する必要はない。GTOバリデーターは、他のトランザクションよりもバンドルのトランザクションを優先するように動機付けられているからである [(00:20:28)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1228s)。
- ブロックエンジンは、バンドル内のトランザクションが有効かどうかを確認する。トランザクションが署名されているか、署名が有効か、バンドル内のトランザクション数が5つ以下かどうかを確認する [(00:20:54)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1254s)。
- バンドル内のトランザクションがすべて成功するかどうかをシミュレートし、バンドルが他のバンドルよりもどれだけ支払うかを確認する [(00:21:13)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1273s)。
- バンドルは、状態を読み書きするグループに分割され、シミュレーションが実行され、支払い額が高い順に並べ替えられる [(00:21:45)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1305s)。
- バンドルは、ブロックエンジンに送信され、ブロックエンジンがバリデーターに転送する [(00:22:14)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1334s)。

## G2パイプラインとSearcher
- G2パイプラインはレイテンシに敏感であり、400ミリ秒以内にブロックを構築する必要がある [(00:22:44)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1364s)。
- Searcherは、トランザクションをブロックエンジンに送信し、ブロックエンジンがバリデーターに転送する [(00:22:35)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1355s)。
- Searcherの例として、Background SearcherとCLIがある [(00:23:31)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1411s)。
- CLIは、Rustプログラムであり、テストバンドルを送信するために使用できる [(00:23:41)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1421s)。
- CLIには、バンドルを送信するためのコマンドラインツールがある [(00:24:05)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1445s)。

## Searcherクライアントの使い方
- Searcherクライアントを使用して、トランザクションをバンドル化し、署名付きのトランザクションを送信する方法を説明している [(00:25:32)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1532s)。
- Searcherクライアントは、トランザクションをバンドル化するために、各トランザクションにメモを追加する必要がある [(00:25:53)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1553s)。
- Searcherクライアントは、トランザクションをバンドル化し、確認を伴うバンドルを送信する必要がある [(00:25:59)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1559s)。
- Searcherクライアントを使用するには、Block Engine URLとキーペアパスが必要である [(00:28:14)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1694s)。
- Searcherクライアントを使用して、Tipアカウントを取得することができる [(00:28:04)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1684s)。
- Searcherクライアントを使用して、特定のアカウントやプログラムに関する情報を取得することができる [(00:29:21)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1761s)。
- Searcherクライアントを使用して、メモリプール内のトランザクションに関する情報を取得することができる [(00:29:26)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1766s)。
- Searcherクライアントを使用して、バンドルを作成するために必要なトランザクションを取得することができる [(00:29:30)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1770s)。
- Searcherクライアントを使用するには、特定のキーペアを使用する必要がある [(00:28:49)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1729s)。
- Searcherクライアントを使用するには、Block Engine URLとキーペアパスを指定する必要がある [(00:28:23)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1703s)。
- Searcherクライアントを使用して、Tipアカウントを取得することができるが、フォーマットは整っていない [(00:29:06)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1746s)。

## リーダーのスケジュール
- 次のリーダーは、約40秒後に到着する予定です。約80スロットあり、スロットは約半秒なので、約40秒になります。 [(00:30:10)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1810s)
- 次のリーダーは、約1分後に到来する予定です。 [(00:30:31)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1831s)
- 次のリーダーは、約50スロット後に到来する予定です。約半分の時間、約30秒です。 [(00:30:40)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1840s)
- リーダーのスケジュールは、通常、約1分以内に更新されます。 [(00:31:08)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1868s)
- 接続されたリーダーは、現在のエポックまたは次のエポックでブロックを生成するリーダーの一覧です。 [(00:31:25)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1885s)

## バンドルの送信と実行
- バンドルを送信するには、RPC、ペイヤー、メッセージ、トランザクション数、ランポートの寄付額、チップアカウントが必要です。 [(00:32:42)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1962s)
- バンドルが送信されると、約5秒後に結果が返されます。 [(00:33:02)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1982s)
- バンドルは、指定されたスロットで指定されたバリデータによって受け入れられ、トランザクションが正常に実行されます。 [(00:33:18)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=1998s)
- トランザクションは、メモプログラムを呼び出し、バリデータにチップを送信します。 [(00:33:27)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2007s)
- トランザクションには、メッセージが含まれます。 [(00:33:43)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2023s)
- CLIはデフォルトでバージョン トランザクション内のメモ命令をビルドし、送信されたトランザクションはこの形式である [(00:34:19)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2059s)。
- つのトランザクションが同じスロット（222164440）に着陸し、ブロック内の非投票トランザクションは8つだけだった [(00:34:44)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2084s)。
- つのトランザクションは連続して実行され、両方とも成功した [(00:35:30)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2130s)。
- バンドル内のトランザクションは順番に実行され、依存関係がある場合にのみ有効になる [(00:36:12)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2172s)。

## バンドルの失敗
- バンドルが失敗すると、トランザクションは実行されず、バンドルは送信されない [(00:38:42)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2322s)。
- バンドルの失敗は、シミュレーション エラー、トランザクション署名のランタイム エラーなどによって発生する可能性がある [(00:38:16)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2296s)。
- バンドルが失敗した場合、トランザクションはクラスターに送信されず、トランザクション署名は見つからない [(00:38:36)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2316s)。

## ブロックエンジンの選択
- ブロックエンジンは、バリデーターに接続する必要があるため、接続先によって待ち時間が異なることがある [(00:39:11)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2351s)。
- 例えば、フランクフルトのブロックエンジンとアムステルダムのブロックエンジンでは、待ち時間が異なる [(00:39:41)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2381s)。
- ニューヨークのブロックエンジンは、米国のバリデーターに接続しているため、待ち時間が短くなる可能性がある [(00:39:52)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2392s)。
- トランザクションが時間に敏感でない場合は、ブロックエンジンの選択はあまり重要ではないが、ラウンドトリップ時間が重要な場合は、ブロックエンジンに近い場所を選択する必要がある [(00:40:34)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2434s)。
- バリデーターの場合は、ブロックエンジンとの近接性が重要である [(00:40:46)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2446s)。
- つのブロックエンジン（[フランクフルト・アム・マイン](https://ja.wikipedia.org/wiki/フランクフルト・アム・マイン)、アムステルダム、[ニューヨーク](https://ja.wikipedia.org/wiki/ニューヨーク)、東京）をテストした結果、待ち時間はそれぞれ異なった [(00:41:12)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2472s)。
- 待ち時間は、ブロックエンジンに接続する距離やネットワーク状況によって異なる [(00:41:58)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2518s)。
- Solanaのスピードを最大限に活用するには、ブロックエンジンとの近接性が重要である [(00:42:54)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2574s)。

## Cheetoのバンドル処理の変更
- Cheetoはバンドルの処理方法を変更し、バンドルを内部的に他のリージョンに転送するようになったため、バンドルの確認時間が短縮された [(00:43:47)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2627s)。
- これにより、バンドルを送信する際に、待機時間が短縮され、バンドルが成功裏に処理される [(00:43:34)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2614s)。
- バンドルを送信する際に、エラーが発生する場合があるが、これはCLIがまだこの機能をサポートしていないためであり、バンドルは正常に処理されている [(00:44:46)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2686s)。
- バンドルを検索することで、バンドルが正常に処理されたことを確認できる [(00:44:59)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2699s)。
- バンドルに含まれるトランザクションは、クロスリージョンで処理されるため、バンドルを送信する際に、リージョンを指定する必要はない [(00:45:40)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2740s)。
- バンドルに含まれるトランザクションは、独立して処理されるため、バンドルに含めるトランザクションを選択する際には、トランザクション間の依存関係を考慮する必要がある [(00:46:38)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2798s)。

## バンドルに含めるトランザクションの選択
- バンドルに含めるトランザクションの例として、トークンをmintするトランザクションと、トークンを送信するトランザクションを示す [(00:47:11)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2831s)。
- バンドルに含めるトランザクションを選択する際には、トランザクション間の依存関係を考慮し、バンドルに含めるトランザクションを選択する必要がある [(00:47:25)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2845s)。

## Jito Bundlesの使用方法（詳細）
- Jito Bundlesを使用するために、バンドルインストラクションを削除し、メモインストラクションとトランスファーインストラクションを保持する必要がある [(00:48:05)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2885s)。
- トランスファーインストラクションでは、Tipアカウントにのみトランスファーする必要がある [(00:48:16)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2896s)。
- つのトランザクションを作成し、最初のトランザクションではトランスファーを実行せず、2番目のトランザクションでトランスファーを実行する必要がある [(00:48:24)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2904s)。
- ペアキーペア、ブロックハッシュ、ランポーターを取得する必要がある [(00:48:33)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2913s)。
- Rust SDKを使用して、手動でインストラクションを作成する方法を学んだ [(00:48:55)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2935s)。
- SPLトークンライブラリを使用して、システムプログラムでアカウントを作成する [(00:49:28)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=2968s)。
- システムプログラムでアカウントを作成し、そのアカウントを別のプログラムに割り当てる必要がある [(00:50:15)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3015s)。
- アカウントを割り当てる前にサイズを変更する必要があるかもしれない [(00:50:25)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3025s)。
- システムインストラクションを使用して、アカウントを新しいオーナーに割り当てる [(00:50:30)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3030s)。
- アカウントキーペアを使用してトランザクションに署名する必要がある [(00:50:41)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3041s)。

## Solana SDKのインストール
- トランザクションを実行するために、Solana SDKクレートをインストールする必要がある [(00:51:23)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3083s)。

## Jito Bundlesのビルドとトランザクション
- Jito Bundlesをビルドする際に、コンパイルするまでの間にビルドの待機時間があることを示している [(00:53:01)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3181s)。
- ビルドが完了すると、バンドルを作成する必要があることを強調している [(00:54:45)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3285s)。
- バンドルを作成する際に、10スロットの待機時間があることを示している [(00:56:41)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3401s)。
- バンドルが受け入れられると、トランザクションが成功することを示している [(00:56:56)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3416s)。
- トランザクションの詳細を確認するために、ブラウザを使用している [(00:57:19)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3439s)。
- トランザクションは、ランダムなアカウントを作成し、ランパードとアカウントを関連付けることを示している [(00:57:29)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3449s)。
- アカウントはアンディに属していることを示しており、これはトランザクションによって作成されたアカウントであることを示唆している [(00:57:38)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3458s)。
- トランザクションは、前のトランザクションに依存していることを示しており、逆の順序で実行することはできないことを示している [(00:58:35)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3515s)。
- J1をチップアドレスに送信し、アカウントを作成するという2つのトランザクションを実行する例が示された [(00:58:45)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3525s)。

## Atomicなトランザクションの実行例
- これらのトランザクションは個別に実行することもできるが、Atomicにしたい場合は、Cheetahブロックエンジンにバンドルとして送信する必要がある [(00:59:48)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3588s)。
- バンドルは、すべてのトランザクションが成功するか、すべて失敗するかのいずれかであることを保証する [(00:59:58)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3598s)。
- トランザクションの順序を変更すると、バンドルは失敗する [(01:00:55)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3655s)。
- バンドルの利点は、トランザクションの1つが失敗すると、他のトランザクションも実行されず、バリデータへの支払いも行われないことである [(01:01:56)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3716s)。

## チュートリアルのまとめ
- このチュートリアルでは、GTOバンドルの基本的な概念と使用方法を理解することが目的である [(01:02:14)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3734s)。
- 将来的には、ArbitrageやLiquidationなどのトピックについても扱う予定である [(01:02:30)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3750s)。
- Rust SDKを使用して独自のトランザクションを作成する方法については、別のビデオで説明されている [(01:02:44)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3764s)。
- 質問や疑問がある場合は、G2 Discordに参加して質問することができる [(01:02:52)](https://www.youtube.com/watch?v=HZ1pK9i6zx4&t=3772s)。
