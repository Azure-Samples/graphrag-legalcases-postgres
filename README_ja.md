# GraphRAG Solution Accelerator for Azure Database for PostgreSQL

このソリューションアクセラレータは、リーガルリサーチコパイロットアプリケーションのエンドツーエンドの例として設計されています。
これは、ベクター検索、セマンティックランキング、Azure Database for PostgreSQLでのGraphRAG、の3つの情報検索技術の実装を示し、それらを組み合わせることで、法律調査の質問に対して高品質な回答を提供できることを示しています。
このアプリは、50万件の法的判例を含む米国の判例法データセットを、実際のデータのソースとして使用しています。
これらの概念の詳細については、[このソリューションアクセラレーターに関するブログ](https://aka.ms/pg-graphrag)をご覧ください。

## ソリューションアクセラレータの設計

<p align="center">
<img src="docs/assets/graph_rag_arch.png" style="width:70%; height:auto; display: block; margin: 0 auto;  text-align:center">
</p>

## ソリューションアクセラレータのコンセプト

アーキテクチャ図が示すように、このソリューションアクセラレーターは **ベクター検索、セマンティックランキング、GraphRAG** を統合しています。以下に、情報検索パイプラインを含む主要なポイントを紹介します:

<details>
  <summary><b>セマンティックランキング</b></summary>
    セマンティックランカーモデルを使用してベクター検索の結果を再ランキングし、上位の結果の関連性を大幅に向上させます（例えば、NDCG@10 の精度が 10～20% 向上）。
    セマンティックランカーは単独のソリューションアクセラレーターとしても利用可能であり、その詳細はブログ「Introducing Semantic Ranker Solution Accelerator for Azure Database for PostgreSQL」に記載されています。
</details>

<details>
  <summary><b>GraphRAG</b></summary>
    Microsoft Research によって提案された高度な RAG 技術であり、ソースデータからナレッジグラフを抽出し、それを活用して LLM により良いコンテキストを提供することで、RAG システムの応答品質を向上させます。GraphRAG 技術は、以下の 3つの高レベルなステップで構成されています:
    1. グラフの抽出
    2. エンティティの要約
    3. クエリ時のグラフクエリ生成
</details>

<details>
  <summary><b>情報検索パイプライン</b></summary>
    特化したグラフクエリをクエリ時に使用することで、引用グラフの構造を活用します。
    このグラフクエリは、法的判例の重要性をシグナルとして利用し、情報検索パイプラインの精度を向上させるよう設計されています。
    グラフクエリは、従来のリレーショナルクエリと OpenCypher グラフクエリを組み合わせた形で表現され、Apache AGE 拡張を使用して Postgres 上で実行されます。
    以下に、最終的な情報検索パイプラインを示します。
    <p align="center"><img src="docs/assets/info_pipeline.png" style="width:70%; height:auto; display: block; margin: 0 auto; text-align:center"></p>
</details>

## さらに詳しく読む

関連するソリューションアクセラレーターや記事については、以下をご覧ください:

- [Introducing GraphRAG Solution for Azure Database for PostgreSQL](https://aka.ms/pg-graphrag)
- [Semantic Ranker Solution Accelerator for Azure Database for PostgreSQL](https://github.com/microsoft/Semantic-Ranker-Solution-PostgreSQL)
- [GraphRAG: Unlocking LLM discovery on narrative private data](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/)
- [Reciprocal Rank Fusion (RRF) explained in 4 mins](https://medium.com/@devalshah1619/mathematical-intuition-behind-reciprocal-rank-fusion-rrf-explained-in-2-mins-002df0cc5e2a)

## デプロイメントと開発

以下の手順は、このソリューションアクセラレーターに必要な Azure サービスを、あなたの Azure サブスクリプションにデプロイする方法を案内します。

### セマンティックランキング ML エンドポイントの前提条件となる手順

⚠️ **注意:** このアクセラレーターのセマンティックランキング機能を実行するには、「bge-reranker-v2-m3」などのランキングモデルを実行する Azure ML エンドポイントが必要です。これをセットアップする方法として、以下の関連するソリューションアクセラレーターをデプロイすることで、ランキングスコアリング用の Azure ML エンドポイントを構築できます。

- [Semantic Ranking in Azure Database for PostgreSQL Flexible Server](https://github.com/microsoft/Semantic-Ranker-Solution-PostgreSQL)

👉 まずは上記のリポジトリに記載された手順に従って設定を完了させてから、以下のデプロイ手順に進んでください。

👉 このアクセラレーターをデプロイした後、`"/score"` REST エンドポイントの URI とキーを記録してください。これらは、以下のデプロイ手順で必要になります。

### Posix (sh) を使用したデプロイ手順

1. 以下のコマンドを入力して、演習リソースを含む GitHub リポジトリをクローンしてください:
    ```bash
    git clone https://github.com/Azure-Samples/graphrag-legalcases-postgres.git
    cd graphrag-legalcases-postgres
    ```
2. サンプルの .env ファイルを使用して、自分用の .env ファイルを作成してください。
    ```bash
    cp .env.sample .env
    ```
3. 作成した .env ファイルを編集し、Azure ML セマンティックランカーのエンドポイントを追加してください。
    - 前提条件の手順で取得した値を使用してください。
    - 各項目の {} 内の値を置き換えてください。
    ```bash
    AZURE_ML_SCORING_ENDPOINT={YOUR-AZURE-ML-ENDPOINT}
    AZURE_ML_ENDPOINT_KEY={YOUR-AZURE-ML-ENDPOINT-KEY}
    AZURE_ML_DEPLOYMENT={YOUR-AZURE-ML-ENDPOINT-KEY}
    ```

    （日本語版追加説明）
    - 他の項目は以下を参考に設定してください。
    ```bash
    # Database Configuration
    POSTGRES_HOST=(Semantic-Ranker-Solution-PostgreSQLの$AZURE_POSTGRES_HOST)
    POSTGRES_USERNAME=(Semantic-Ranker-Solution-PostgreSQLの$AZURE_POSTGRES_USERNAME)
    POSTGRES_PASSWORD=(Semantic-Ranker-Solution-PostgreSQLで"postgresAdminLoginPassword"として入力したパスワード）
    POSTGRES_DATABASE=(Semantic-Ranker-Solution-PostgreSQLの$AZURE_POSTGRES_DB_NAME)
    POSTGRES_SSL=enable

    # Workspace Path
    WORKSPACE=/workspace

    # PostgreSQL User Configuration
    POSTGRES_USER_ID=1000
    POSTGRES_USER_NAME=postgres
    POSTGRES_USER_SHELL=/bin/bash

    # PostgreSQL and pgenv Versions
    PGENV_VERSION=1.3.7
    PG_VERSION=16.8

    # OpenAI Configuration
    OPENAI_CHAT_HOST=azure
    OPENAI_EMBED_HOST=azure

    # Azure ML Configuration
    AZURE_ML_SCORING_ENDPOINT=(Semantic-Ranker-Solution-PostgreSQLで保存したAzure MLのエンドポイント情報)
    AZURE_ML_ENDPOINT_KEY=(Semantic-Ranker-Solution-PostgreSQLで保存したAzure MLのアクセスキー)
    AZURE_ML_DEPLOYMENT=bge-v2-m3-1
    ```

4. Azure アカウントにログインします。
    ```bash
    azd auth login
    ```
5. リソースをプロビジョニングします。
    ```bash
    azd up
    ```
    - リソースグループに使用する名前を入力してください。
    - これにより、Azure Database for PostgreSQL Flexible Server、Azure OpenAI Service、Azure Container App Service を含む Azure リソースがプロビジョニングされ、このサンプルがそれらのリソースにデプロイされます。

### Windows (PowerShell) を使用したデプロイ手順

このソリューションでは sh シェルの使用を推奨しており、sh シェルに最適化されています。
Windows 環境であっても、Visual Studio Code で Ctrl + Shift + P を押し、“Dev Containers: Rebuild and Reopen in Container” オプションを選択することで、提供された Devcontainer セットアップを実行できます。
これにより、sh シェルを利用できる環境が整い、作業を進めることができます。

ですが、Windows 環境で直接 PowerShell (pwsh) を使用することを希望する場合は、以下の手順に従ってください。:

1. [azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd?tabs=winget-windows%2Cbrew-mac%2Cscript-linux&pivots=os-windows) をインストールします。

2. [PowerShell (PowerShell-7.4.6-win-x64.msi)](https://github.com/PowerShell/PowerShell/releases/tag/v7.4.6) をインストールします。

3. [Rust (rustup-init.exe)](https://rustup.rs/) をインストールします。

4. [Python 3.12 (Windows installer (64-bit))](https://www.python.org/downloads/release/python-3120/) をインストールします。

5. [Node.js](https://nodejs.org/en) をインストールします。

その後、新しいターミナルを開き、以下の2つのコマンドを手動で実行する必要があります。なお、Linux ではこれらを手動で実行する必要はありませんが、Windows では実行が必要です:

```bash
pip install -r requirements-dev.txt
pip install -e src/backend
```

上記の手順を完了した後、[Deployment Steps For using Posix (sh)](#deployment-steps-for-using-posix-sh) の手順に従ってデプロイを進めてください。

## トラブルシューティング

### よくある問題と解決方法

1. **デプロイ中のエラー (`azd up`)**
   デプロイプロセス中にエラーが発生した場合は、`azd down` を実行してリソースをクリーンアップし、問題を解決してください。問題が解決したら、`azd up` を再実行してデプロイを再試行できます。

2. **URLや設定が見つからない**
   デプロイした URL や設定を見失った場合は、`azd show` コマンドを実行することで、既存の URL やその他のデプロイ詳細を確認できます。

3. **リージョンの容量をチェックする**
   `azd up` を実行する前に、対象のリージョンにデプロイに必要な十分なキャパシティがあることを確認してください。
   必要なキャパシティは `main.parameters.json` ファイルで確認できます。これは、Chat、Eval、および Embedding の生成に必要なリソースを示しています。

   デフォルトでは、以下の最小キャパシティを確保する必要があります。
   もし Azure サブスクリプション内に十分なキャパシティがない場合は、`main.parameters.json` のパラメータを適宜変更して対応してください。
     - **GPT-4o:** 30K - AZURE_OPENAI_CHAT_DEPLOYMENT_CAPACITY
     - **GPT-4:** 80K - AZURE_OPENAI_EVAL_DEPLOYMENT_CAPACITY
     - **text-embedding-3-small:** 120K - AZURE_OPENAI_EMBED_DEPLOYMENT_CAPACITY

4. **Azure サブスクリプションの権限**
   Azure サブスクリプション内で適切な権限を持っていることを確認してください。リソースを正常にデプロイし、必要な機能を有効にするために、**サブスクリプションの所有者** または同等の権限が必要です。

### MSR GraphRAG 統合（オプション）

フロントエンドから対応するオプションを選択することで、MSR GraphRAG データとのデフォルト統合を実行できます。
しかし、Microsoft の GraphRAG 統合全体を当社の RRF グラフソリューションと併用したい場合は、以下の手順に従って graphrag フォルダーを初期化、オートチューニング、およびインデックス化してください。
GraphRAG の処理結果はすでにデータフォルダー内に用意されています。
ただし、自分でライブラリを実行したい場合は、以下の手順に従ってください。
提供された CSV ファイルをそのまま使用したい場合は、手順 8 へ進んでください。

### 1. 必要なフォルダ構造を作成します

以下のコマンドを実行して、必要なフォルダ構造を作成します:

```bash
mkdir -p ./graphrag/input
```

GraphRAG ライブラリを実行する前に、入力 CSV ファイルを準備し、`./graphrag/input` フォルダーに配置する必要があります。この後の手順で、入力 CSV ファイルを作成します。

### 2. 元のテーブルから関連データを抽出する

元のケーステーブルには、以下を含む複数の列が含まれています:

- `id` – 各ケースの一意の識別子
- `data` – 詳細なケース情報を含む大きな JSON オブジェクト
- `description_vector` – ベクター検索に使用される 1536 次元のベクトル

しかし、GraphRAG の処理には `data` 内のすべての JSON フィールドが必要なわけではありません。
データセットを簡素化するために、必要な列のみを保持し、`description_vector` を除外したフィルタリング済みのテーブル (`cases_filtered`) を作成します。
次の手順で、このテーブルから CSV ファイルを作成します。

```sql
CREATE TABLE cases_filtered (
    id TEXT,
    name TEXT,
    court_id TEXT,
    court_name TEXT,
    description TEXT
);

INSERT INTO cases_filtered (id, name, court_id, court_name, description)
SELECT
    id,
    data->>'name' AS name,
    (data->'court'->>'id') AS court_id,
    data->'court'->>'name' AS court_name,
    data->'casebody'->'opinions'->0->>'text' AS description
FROM cases_updated;
```

元のcaseテーブルは、`azd up` コマンドの実行後に `cases_final.csv` としてデータフォルダー内に提供されています。
このファイルを取得すると、`cases_updated` という名前のテーブル形式で利用できます。

### 3. データをCSVに出力する

必要な CSV ファイルを生成するには、PostgreSQL データベース内で以下の SQL コマンドを実行してください:

```sql
COPY (
    SELECT id, name, court_id, court_name, description
    FROM demo_cases_filtered
) TO '/home/postgres/cases_filtered_final.csv'
WITH CSV HEADER;
```

このコマンドは、`demo_cases_filtered` から必要なフィールドを抽出し、`cases_filtered_final.csv` として PostgreSQL コンテナ内に保存します。

### 4. CSV ファイルを入力ディレクトリにコピーする

次に、生成された CSV ファイルを PostgreSQL コンテナからローカルの入力ディレクトリにコピーします。

```bash
docker cp <container-name>:/home/postgres/cases_filtered_final.csv /<your-path>/graphrag/input/cases_filtered_final.csv
```

`<container-name>` を実際に稼働している PostgreSQL コンテナの名前に、`<your-path>` を GraphRAG の入力フォルダーがあるローカルディレクトリのパスに置き換えてください。

`cases_filtered_final.csv` が `./graphrag/input/` 内に正しく配置されていることを確認してから、GraphRAG ライブラリを実行してください。

### 5. 依存関係をインストールする

Poetry 環境を有効化するには、以下のコマンドを実行します:

```bash
poetry shell
poetry install
```

このコマンドは、`graphrag` コマンドを使用するための必要な依存関係をインストールします。

### 6. フォルダを初期化する

フォルダを初期化するには、以下のコマンドを実行します:

```bash
graphrag init --root ./graphrag
```

これにより、プロセスに必要なファイルが作成されます。

### 7. API キーと設定を構成する

- 使用している OpenAI モデルの種類に応じて、`.env` ファイルに `GRAPHRAG_API_KEY` を設定してください。
- `settings.yaml` ファイルを更新し、以下の設定中のデータ列を置き換えてください:

```yaml
input:
  type: file  # or 'blob'
  file_type: csv  # or 'text'
  base_dir: "input"
  file_encoding: utf-8
  file_pattern: ".*\\.csv$"
  source_column: id
  text_column: description
  title_column: name
  document_attribute_columns:
    - court_id
    - court_name
```

- `settings.yaml` ファイルを更新し、Azure OpenAI 用の以下のモデル設定を適用してください。

```yaml
llm:
  api_key: ${GRAPHRAG_API_KEY}
  type: azure_openai_chat
  model: gpt-4o-mini
  model_supports_json: true
  api_base: https://<your-azure-openai>.openai.azure.com
  api_version: <your-azure-openai-4o-mini-version>
  deployment_name: gpt-4o-mini
```

```yaml
embeddings:
  async_mode: threaded # or asyncio
  vector_store:
    type: lancedb
    db_uri: 'output/lancedb'
    container_name: default
    overwrite: true
  llm:
    api_key: ${GRAPHRAG_API_KEY}
    type: azure_openai_embedding
    model: text-embedding-3-small
    api_base: https://<your-azure-openai>.openai.azure.com
    api_version: <your-azure-openai-text-embedding-3-small-version>
    deployment_name: text-embedding-3-small
```

### 8. プロンプトのオートチューニングを実行する

以下のコマンドを実行して、データに応じたプロンプトのオートチューニングを行います:

```bash
python -m graphrag prompt-tune --root ./graphrag/ --config ./graphrag/settings.yaml --no-discover-entity-types --output ./graphrag/prompts/
```

### 9. インデックス作成プロセスを実行する

以下のコマンドを実行して、ナレッジグラフのインデックス作成プロセスを開始します:

```bash
graphrag index --root ./graphrag
```

このプロセスは、レート制限によっては約1時間かかる場合があります。

### 10. Parquet ファイルを CSV に変換する

インデックス作成後、`notebook.ipynb` ファイルを使用して、以下の Parquet ファイルを CSV に変換し、`data` フォルダーに保存します:

- `final_documents`
- `final_text_units`
- `final_communities`
- `final_community_reports`

CSV ファイルが `data` フォルダーに保存されたら、次のステップに進み、追加のベクターフィールドを作成し、埋め込みを生成してください。

### 11. 埋め込みの生成

埋め込み（Embeddings）は、`final_text_units` および `final_community_reports` の CSV ファイルを変更するために、プロビジョニング後に生成する必要があります。

初回のデプロイを実行する前に、`scripts/setup_postgres_seeddata.sh` ファイル内の RUN_POST_EMBEDDING パラメータを `true` に設定してください。
これにより、新しいフィールドが作成され、埋め込み（Embeddings）が生成されます。その後、以下のコマンドを実行してください。

```bash
azd up
```

埋め込み（Embeddings）を含むテーブルが生成されたら、それらを CSV ファイルに変換し、`data` フォルダーに配置してください。これにより、今後のデプロイが高速化されます。

### 12. プロジェクトをデプロイする

最後に、埋め込み（Embeddings）を生成し、CSV 形式で保存した後、`scripts/setup_postgres_seeddata.sh` ファイル内の RUN_POST_EMBEDDING パラメータを `false` に更新してください。
これにより、不要な再処理を防ぐことができます。

以下のコマンドを実行して、デプロイを完了してください。:

```bash
azd up
```

サーバーがすでに稼働している場合は、以下のコマンドを最初に実行して、サーバーを再プロビジョニングしてください:

```bash
azd down
```

## 確認事項

- `.env` および `settings.yaml` 内のすべての必要な設定が正確であることを確認してください。
- インデックス作成の時間は、システムの性能やレート制限によって異なる場合があります。
- 問題が発生した場合は、ドキュメントを参照するか、サポートに問い合わせてください。

## コントリビューション

このプロジェクトは、コントリビューションや提案を歓迎しています。
多くの場合、Contributor License Agreement (CLA) への同意が必要です。
CLA では、コントリビューターがそのコントリビューションを使用する権利を当社に与える権利を持ち、実際にそれを許可することを宣言する必要があります。

詳細については、[https://cla.microsoft.com](https://cla.microsoft.com) をご覧ください。

プルリクエストを送信すると、CLA-bot が自動的に判定し、CLA の提出が必要かどうかを確認します。
必要な場合は、PR に適切なラベルやコメントが追加されます。
ボットが提供する指示に従って手続きを進めてください。
なお、一度 CLA に同意すれば、当社の CLA を使用するすべてのリポジトリで再度提出する必要はありません。

このプロジェクトは、[Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/) を採用しています。
詳細については、[Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) をご覧いただくか、追加の質問やコメントがある場合は [opencode@microsoft.com](mailto:opencode@microsoft.com) までお問い合わせください。

## 商標

Microsoft の商標やロゴの認可された使用は、[Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general) に従う必要があります。
本プロジェクトの改変版で Microsoft の商標やロゴを使用する場合、それが混乱を招いたり、Microsoft のスポンサーシップを示唆したりしないようにしなければなりません。
また、第三者の商標やロゴを使用する場合は、それぞれの第三者のポリシーに従う必要があります。
