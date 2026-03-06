import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as apigw from 'aws-cdk-lib/aws-apigateway';

export class AppStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string) {
    super(scope, id);

    // ── S3 for static assets ────────────────────────────────────
    const assetsBucket = new s3.Bucket(this, 'AssetsBucket', {
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // Upload static assets from OpenNext build
    new s3deploy.BucketDeployment(this, 'DeployAssets', {
      sources: [s3deploy.Source.asset('.open-next/assets')],
      destinationBucket: assetsBucket,
    });

    // ── Next.js SSR Lambda ──────────────────────────────────────
    const nextjsLambda = new lambda.Function(this, 'NextjsSSR', {
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('.open-next/server-function'),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(30),
      environment: {
        NEXT_PUBLIC_API_URL: process.env.API_URL || '',
      },
    });

    // ── FastAPI Backend Lambda ──────────────────────────────────
    const backendLambda = new lambda.Function(this, 'FastAPIBackend', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'main.lambda_handler',  // your existing Mangum handler
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
    });

    // ── API Gateway for Backend ─────────────────────────────────
    const api = new apigw.LambdaRestApi(this, 'BackendAPI', {
      handler: backendLambda,
      proxy: true,
    });

    // ── CloudFront Distribution ─────────────────────────────────
    const distribution = new cloudfront.Distribution(this, 'CDN', {
      defaultBehavior: {
        // SSR requests → Next.js Lambda
        origin: new origins.FunctionUrlOrigin(
          nextjsLambda.addFunctionUrl({
            authType: lambda.FunctionUrlAuthType.NONE,
          })
        ),
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      additionalBehaviors: {
        // Static assets → S3
        '_next/static/*': {
          origin: new origins.S3Origin(assetsBucket),
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        },
        // API calls → API Gateway
        'api/*': {
          origin: new origins.HttpOrigin(
            `${api.restApiId}.execute-api.${this.region}.amazonaws.com`
          ),
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        },
      },
    });

    new cdk.CfnOutput(this, 'URL', { value: distribution.domainName });
  }
}