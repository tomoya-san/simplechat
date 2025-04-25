# lambda/index.py
import json
import os
import boto3
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError
from urllib import request


# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
bedrock_client = None

# モデルID
MODEL_ID = "google/gemma-2-2b-jpn-it"

# APIエンドポイント
ENDPOINT = "https://cbd6-34-16-172-104.ngrok-free.app/"

def lambda_handler(event, context):
    try:
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        print("The request body: ", body)
        print("Processing message:", message)
        print("Using model:", MODEL_ID)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # invoke_model用のリクエストペイロード
        request_payload = {
            "messages": messages,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        request_payload = json.dumps(request_payload).encode("utf-8")
        
        print("Calling FastAPI generate with payload:", request_payload)
        
        # APIを呼び出し
        generate_request = request.Request(ENDPOINT + "generate_with_history", data=request_payload, method="POST")
        generate_request.add_header("Content-Type", "application/json")
        with request.urlopen(generate_request) as response:
            response_bytes = response.read() # <- raw bytes
            response_json = json.loads(response_bytes) # <- JSON
        
        # レスポンスを解析
        print("FastAPI response:", response_json)
        
        # 応答の検証
        # if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
        #     raise Exception("No response content from the model")
        
        # アシスタントの応答を取得
        assistant_response = response_json["generated_text"]
        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
