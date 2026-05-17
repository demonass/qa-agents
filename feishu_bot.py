#!/usr/bin/env python3
"""
飞书 QA Agent 机器人服务

使用说明：
1. 在飞书开放平台创建机器人，获取 App ID 和 App Secret
2. 修改下方配置信息
3. 运行：python feishu_bot.py
4. 在飞书客户端搜索机器人名称并添加
"""

import os
import json
import time
import hmac
import hashlib
from flask import Flask, request, make_response

# 在导入前移除代理环境变量
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

from main import create_qa_agent
from config.settings import is_kong_mode, LLMConfig, get_kong_models

# ==================== 配置区域 ====================
APP_ID = "your_app_id"  # 替换为您的 App ID
APP_SECRET = "your_app_secret"  # 替换为您的 App Secret
VERIFICATION_TOKEN = "your_verification_token"  # 替换为您的 Verification Token
PORT = 5000

# Kong 模式下飞书机器人使用的默认模型
DEFAULT_MODEL = LLMConfig.KONG_DEFAULT_MODEL if is_kong_mode() else ""
# ==================================================

app = Flask(__name__)
qa_agent = create_qa_agent().compile()

# 打印启动信息
if is_kong_mode():
    print(f"🔄 飞书机器人运行在 Kong 多模型模式")
    print(f"📡 Kong 网关: {LLMConfig.KONG_BASE_URL}")
    print(f"🤖 默认模型: {DEFAULT_MODEL}")
else:
    print(f"🔄 飞书机器人运行在单模型模式")
    print(f"📡 LLM 服务: {LLMConfig.BASE_URL}")

def get_tenant_access_token():
    """获取租户访问令牌"""
    import requests
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取 token 失败: {e}")
        return None

def verify_signature(request):
    """验证飞书签名"""
    timestamp = request.headers.get("X-Lark-Request-Timestamp")
    nonce = request.headers.get("X-Lark-Request-Nonce")
    signature = request.headers.get("X-Lark-Signature")
    
    if not timestamp or not nonce or not signature:
        return False
    
    # 构建签名字符串
    sign_string = f"{timestamp}{nonce}{VERIFICATION_TOKEN}"
    hash_result = hmac.new(
        VERIFICATION_TOKEN.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return hash_result == signature

def send_message(open_id, content):
    """发送消息给用户"""
    import requests
    
    token = get_tenant_access_token()
    if not token:
        return False
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {token}"
    }
    
    data = {
        "receive_id": open_id,
        "receive_id_type": "open_id",
        "content": json.dumps({"text": content}),
        "msg_type": "text"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"发送消息失败: {e}")
        return False

@app.route("/feishu/webhook", methods=["GET", "POST"])
def webhook():
    """飞书机器人 webhook 入口"""
    # GET 请求用于验证
    if request.method == "GET":
        challenge = request.args.get("challenge")
        return make_response(challenge)
    
    # POST 请求处理消息
    if not verify_signature(request):
        return make_response("Invalid signature", 401)
    
    try:
        data = request.get_json()
        event = data.get("event", {})
        
        # 只处理消息事件
        if event.get("type") != "message":
            return make_response("OK")
        
        message = event.get("message", {})
        user_id = event.get("sender", {}).get("sender_id", {}).get("open_id")
        text = message.get("content", "")
        
        # 解析消息内容
        try:
            content = json.loads(text)
            user_input = content.get("text", "").strip()
        except:
            user_input = text.strip()
        
        if not user_input or user_id is None:
            return make_response("OK")
        
        # 跳过机器人自己发送的消息
        if message.get("sender_type") == "app":
            return make_response("OK")
        
        print(f"📩 收到消息: {user_input}")
        
        # 构建初始状态
        initial_state = {
            "user_input": user_input,
            "language": "中文",
            "intent_type": "",
            "template_path": "",
            "template_content": "",
            "requirement": user_input,
            "document_content": "",
            "output_content": "",
            "iteration": 0,
            "code_analysis": "",
            "rag_context": "",
            "selected_model": DEFAULT_MODEL  # Kong 模式下使用默认模型
        }
        
        # 调用 QA Agent
        final_state = qa_agent.invoke(initial_state)
        response_content = final_state.get("output_content", "抱歉，我无法处理这个请求。")
        
        # 发送回复
        send_message(user_id, response_content)
        print(f"💬 已回复: {response_content[:30]}...")
        
    except Exception as e:
        print(f"处理消息失败: {e}")
    
    return make_response("OK")

if __name__ == "__main__":
    print(f"🚀 飞书 QA Agent 机器人启动中...")
    print(f"📡 Webhook 地址: http://localhost:{PORT}/feishu/webhook")
    print(f"⚠️ 请确保此地址可以被飞书服务器访问（需要公网 IP）")
    app.run(host="0.0.0.0", port=PORT, debug=True)
