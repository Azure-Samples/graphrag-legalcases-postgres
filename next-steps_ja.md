# `azd init` 後の追加の手順

## 索引

1. [Next Steps](#next-steps)
2. [What was added](#what-was-added)
3. [Billing](#billing)
4. [Troubleshooting](#troubleshooting)

## Next Steps

### インフラをプロビジョニングし、アプリケーションコードをデプロイする

`azd up` を実行して、インフラをプロビジョニングし、Azure にデプロイしてください。または、`azd provision` を実行してインフラをプロビジョニングし、その後 `azd deploy` を実行してデプロイを個別に実行することもできます。
リストされたサービスのエンドポイントにアクセスして、アプリケーションが正常に稼働していることを確認してください！

問題を解決するには、[Troubleshooting](#troubleshooting) を参照してください。

### 実行するサービスの環境変数を設定する

[main.parameters.json](./infra/main.parameters.json) の `settings` を更新して、実行するサービスの環境変数を設定してください。

### CI/CD パイプラインを設定する

1. ローカルにワークフローパイプラインファイルを作成してください。以下のスターターが利用可能です:
   - [Deploy with GitHub Actions](https://github.com/Azure-Samples/azd-starter-bicep/blob/main/.github/workflows/azure-dev.yml)
   - [Deploy with Azure Pipelines](https://github.com/Azure-Samples/azd-starter-bicep/blob/main/.azdo/pipelines/azure-dev.yml)

2. `azd pipeline config` を実行して、Azure に安全に接続するようデプロイメントパイプラインを設定してください。

## What was added

### インフラストラクチャの構成

インフラとアプリケーションを記述するために、azure.yaml と Bicep を使用した Infrastructure as Code ファイルが追加され、以下のディレクトリ構造になっています:

```yaml
- azure.yaml     # azd プロジェクトの設定
- infra/         # Infrastructure as Code (bicep) ファイル
  - main.bicep   # メインデプロイメントのモジュール
  - app/         # アプリケーションリソースのモジュール
  - shared/      # 共有リソースのモジュール
  - modules/     # ライブラリのモジュール
```

各 Bicep ファイルは、プロビジョニングされるリソースを定義しています。これらのリソースは、`azd up` または `azd provision` を実行するとプロビジョニングされます。

- [app/backend.bicep](./infra/app/backend.bicep) - Azure Container Apps のリソースを使用して、`backend` サービスをホストします。
- [app/frontend.bicep](./infra/app/frontend.bicep) - Azure Container Apps のリソースを使用して、`frontend` サービスをホストします。
- [shared/keyvault.bicep](./infra/shared/keyvault.bicep) - Azure KeyVault を使用して、シークレットを保存します。
- [shared/monitoring.bicep](./infra/shared/monitoring.bicep) - Azure Log Analytics ワークスペースと Application Insights を使用して、ログとインストルメンテーション ログを記録および保存します。
- [shared/registry.bicep](./infra/shared/registry.bicep) - Azure Container Registry を使用して、Docker イメージを保存します。

より詳細については [Bicep](https://aka.ms/bicep) を参照してください。

### ソースからビルド（Dockerfile を使わない）

#### Oryx を使用して Buildpacks でビルドする

プロジェクトに Dockerfile が含まれていない場合、[Buildpacks](https://buildpacks.io/) で、[Oryx](https://github.com/microsoft/Oryx/blob/main/doc/README.md) を利用して `azure.yaml` 内のサービスのイメージを作成し、コンテナ化されたアプリを Azure にデプロイします。

ローカルで Docker イメージを作成し、実行するには:

1. `azd package` を実行して、イメージをビルドします。
2. 表示された **Image Tag** をコピーします。
3. `docker run -it <Image Tag>` を実行して、ローカルでイメージを実行してください。

#### ポートを公開する

Oryx は `PORT` をデフォルトで `80`（Java の場合は `8080`）に自動設定します。さらに、`gunicorn` や `ASP .NET Core` などのサポートされている Web サーバーを自動設定し、指定された `PORT` でリッスンするように構成します。
アプリケーションが `PORT` 変数で指定されたポートをすでにリッスンしている場合、追加の設定なしでそのまま動作します。そうでない場合は、以下のいずれかの手順を実行する必要があります:

1. アプリケーションのコードまたは設定を更新し、`PORT` 変数で指定されたポートをリッスンするようにしてください。
1. （別の方法として）`infra/app` フォルダー内の .bicep ファイルで `targetPort` を検索し、アプリケーションが使用するポートに一致するように変数を更新してください。

## Billing

Azure ポータルの「コストの管理と請求」ページを訪れ、現在の支出を追跡してください。Azure サブスクリプションで発生したコストの請求方法や監視方法の詳細については、[課金方法](https://learn.microsoft.com/azure/developer/intro/azure-developer-billing)をご覧ください。

## Troubleshooting

Q: リストされたサービスエンドポイントにアクセスしたところ、空白のページ、一般的なウェルカムページ、またはエラーページが表示されました。

A: サービスが起動に失敗しているか、いくつかの設定が不足している可能性があります。詳細を調査するには、以下の手順を試してください:

1. `azd show` を実行してください。「View in Azure Portal」の下に表示されるリンクをクリックすると、Azure ポータルでリソースグループを開くことができます。
2. デプロイに失敗している特定の Container App サービス に移動してください。
3. 「Revisions with Issues」 の下に表示されている、問題が発生しているリビジョンをクリックしてください。
4. 「Status details」 を確認し、障害の種類に関する詳細情報を確認してください。
5. コンソールログストリーム および システムログストリーム のログ出力を確認し、エラーを特定してください。
6. ログがディスクに書き込まれている場合は、ナビゲーション内の 「Console」 を使用して、実行中のコンテナ内のシェルに接続してください。

詳しいトラブルシューティング情報については、[コンテナー アプリのトラブルシューティング](https://learn.microsoft.com/azure/container-apps/troubleshooting) をご覧ください。

### 追加情報

`azd` プロジェクトのセットアップに関する追加情報については、[Azure Developer CLI テンプレートの作成の概要](https://learn.microsoft.com/azure/developer/azure-developer-cli/make-azd-compatible?pivots=azd-convert) をご覧ください。
