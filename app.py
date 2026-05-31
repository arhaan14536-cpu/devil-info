from flask import Flask, request, jsonify
import sys
import jwt
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import data_pb2
import uid_generator_pb2
import my_pb2
import output_pb2
from datetime import datetime
import json
import time
import urllib3
import warnings
from flask import Flask, Response
import json
from collections import OrderedDict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=UserWarning, message="Unverified HTTPS request")

app = Flask(__name__)

AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def encrypt_message(data_bytes):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data_bytes, AES.block_size))

def encrypt_message_hex(data_bytes):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = cipher.encrypt(pad(data_bytes, AES.block_size))
    return binascii.hexlify(encrypted).decode('utf-8')

def get_base_url(server_name):
    server_name = server_name.upper()
    if server_name == "IND":
        return "https://client.ind.freefiremobile.com/"
    elif server_name in {"BD", "US", "SAC", "NA"}:
        return "https://clientbp.ggwhitehawk.com/"
    else:
        return "https://clientbp.ggblueshark.com/"

def get_server_from_token(token):
    """Extract server region from JWT token"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        lock_region = decoded.get("lock_region", "IND")
        return lock_region.upper()
    except:
        return "IND"

def retry_operation(max_retries=10, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if result and result.get('status') in ['success', 'failed']:
                        return result
                    # Agar result nahi aaya toh retry karo
                    print(f"Attempt {attempt + 1}/{max_retries} failed, retrying...")
                except Exception as e:
                    last_exception = e
                    print(f"Attempt {attempt + 1}/{max_retries} failed with error: {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(delay)
            
            if last_exception:
                return {
                    "status": "error",
                    "message": f"All {max_retries} attempts failed",
                    "error": str(last_exception)
                }
            return {
                "status": "error", 
                "message": f"All {max_retries} attempts failed"
            }
        return wrapper
    return decorator

def get_token_from_uid_password(uid, password):
    """Get JWT token using UID and password - FIXED VERSION"""
    try:
        oauth_url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        payload = {
            'uid': uid,
            'password': password,
            'response_type': "token",
            'client_type': "2",
            'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            'client_id': "100067"
        }
        
        headers = {
            'User-Agent': "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;pt;BR;)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip"
        }

        oauth_response = requests.post(oauth_url, data=payload, headers=headers, timeout=10, verify=False)
        oauth_response.raise_for_status()
        
        oauth_data = oauth_response.json()
        
        if 'access_token' not in oauth_data:
            return None, "OAuth response missing access_token"

        access_token = oauth_data['access_token']
        open_id = oauth_data.get('open_id', '')
        
        platforms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        
        for platform_type in platforms:
            result = try_platform_login(open_id, access_token, platform_type)
            if result and 'token' in result:
                return result['token'], None
        
        return None, "Login successful but JWT generation failed on all platforms"

    except requests.RequestException as e:
        return None, f"OAuth request failed: {str(e)}"
    except ValueError:
        return None, "Invalid JSON response from OAuth service"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def try_platform_login(open_id, access_token, platform_type):
    """Try login for a specific platform - IMPROVED VERSION"""
    try:
        game_data = my_pb2.GameData()
        game_data.timestamp = "2024-12-05 18:15:32"
        game_data.game_name = "free fire"
        game_data.game_version = 1
        game_data.version_code = "1.108.3"
        game_data.os_info = "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)"
        game_data.device_type = "Handheld"
        game_data.network_provider = "Verizon Wireless"
        game_data.connection_type = "WIFI"
        game_data.screen_width = 1280
        game_data.screen_height = 960
        game_data.dpi = "240"
        game_data.cpu_info = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
        game_data.total_ram = 5951
        game_data.gpu_name = "Adreno (TM) 640"
        game_data.gpu_version = "OpenGL ES 3.0"
        game_data.user_id = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
        game_data.ip_address = "172.190.111.97"
        game_data.language = "en"
        game_data.open_id = open_id
        game_data.access_token = access_token
        game_data.platform_type = platform_type
        game_data.field_99 = str(platform_type)
        game_data.field_100 = str(platform_type)

        serialized_data = game_data.SerializeToString()
        encrypted_data = encrypt_message(serialized_data)
        hex_encrypted_data = binascii.hexlify(encrypted_data).decode('utf-8')

        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53"
        }
        
        edata = bytes.fromhex(hex_encrypted_data)

        response = requests.post(url, data=edata, headers=headers, timeout=10, verify=False)
        response.raise_for_status()

        if response.status_code == 200:

            data_dict = None
            try:
                example_msg = output_pb2.Garena_420()
                example_msg.ParseFromString(response.content)
                data_dict = {field.name: getattr(example_msg, field.name)
                             for field in example_msg.DESCRIPTOR.fields
                             if field.name not in ["binary", "binary_data", "Garena420"]}
            except Exception as e:
                try:
                    data_dict = response.json()
                except ValueError:
                    return None

            if data_dict and "token" in data_dict:
                token_value = data_dict["token"]
                try:
                    decoded_token = jwt.decode(token_value, options={"verify_signature": False})
                except Exception:
                    decoded_token = {}

                return {
                    "account_id": decoded_token.get("account_id"),
                    "account_name": decoded_token.get("nickname"),
                    "open_id": open_id,
                    "access_token": access_token,
                    "platform": decoded_token.get("external_type"),
                    "region": decoded_token.get("lock_region"),
                    "status": "success",
                    "token": token_value
                }
        
        return None

    except Exception:
        return None

def create_info_protobuf(uid):
    message = uid_generator_pb2.uid_generator()
    message.saturn_ = int(uid)
    message.garena = 1
    return message.SerializeToString()

def get_player_info(target_uid, token, server_name=None):
    """Get detailed player information"""
    try:
        if not server_name:
            server_name = get_server_from_token(token)
            
        protobuf_data = create_info_protobuf(target_uid)
        encrypted_data = encrypt_message_hex(protobuf_data)
        endpoint = get_base_url(server_name) + "GetPlayerPersonalShow"

        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB53"
        }

        response = requests.post(endpoint, data=bytes.fromhex(encrypted_data), headers=headers, verify=False)
        
        if response.status_code != 200:
            return None

        hex_response = response.content.hex()
        binary = bytes.fromhex(hex_response)
        
        info = data_pb2.AccountPersonalShowInfo()
        info.ParseFromString(binary)
        
        return info
    except Exception as e:
        print(f"Error getting player info: {e}")
        return None

def extract_player_info(info_data):
    if not info_data:
        return None

    b = info_data.basic_info
    p = getattr(info_data, "profile_info", None)
    s = getattr(info_data, "social_info", None)
    pet = getattr(info_data, "pet_info", None)
    clan = getattr(info_data, "clan_basic_info", None)
    credit = getattr(info_data, "credit_score_info", None)

    return {
        # ================= BASIC =================
        "uid": b.account_id,
        "nickname": b.nickname,
        "level": b.level,
        "exp": b.exp,
        "region": b.region,
        "likes": b.liked,
        "release_version": b.release_version,
        "create_at": b.create_at,
        "last_login": b.last_login_at,

        # ================= RANK =================
        "rank": b.rank,
        "ranking_points": b.ranking_points,
        "max_rank": b.max_rank,
        "cs_rank": b.cs_rank,
        "cs_points": b.cs_ranking_points,
        "peak_rank_pos": b.peak_rank_pos,

        # ================= SOCIAL =================
        "gender": s.gender if s else None,
        "language": s.language if s else None,

        "region_stats": {
            "matches": s.region_stats[0].total_matches if s and s.region_stats else None,
            "wins": s.region_stats[0].wins if s and s.region_stats else None,
            "highest_rank": s.region_stats[0].highest_rank if s and s.region_stats else None,
        } if s else None,

        # ================= PET =================
        "pet": {
            "id": pet.pet_id if pet else None,
            "name": pet.pet_name if pet else None,
            "level": pet.level if pet else None,
            "selected_skill": pet.selected_skill_id if pet else None
        } if pet else None,

        # ================= CLAN =================
        "clan": {
            "id": clan.clan_id if clan else None,
            "name": clan.clan_name if clan else None,
            "level": clan.clan_level if clan else None,
            "members": clan.current_members if clan else None,
            "max_members": clan.max_members if clan else None
        } if clan else None,

        # ================= CREDIT =================
        "credit_score": {
            "score": credit.score if credit else None,
            "status": credit.status if credit else None
        } if credit else None,

        # ================= META =================
        "status": "success",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def decode_author_uid(token):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("account_id") or decoded.get("sub")
    except:
        return None

@app.route('/player_info', methods=['GET'])
def player_info_custom():
    """URL: /player_info?uid={uid}&password={password}&friend_uid={target_uid}"""
    uid = request.args.get('uid')
    password = request.args.get('password')
    friend_uid = request.args.get('friend_uid')
    server_name = request.args.get('server_name', 'IND')

    if not uid or not password or not friend_uid:
        return jsonify({"status": "failed", "message": "Missing uid, password, or friend_uid"}), 400

    token, error = get_token_from_uid_password(uid, password)
    if error:
        return jsonify({"status": "failed", "message": error}), 400

    player_info = get_player_info(friend_uid, token, server_name)
    if not player_info:
        return jsonify({"status": "failed", "message": "Info not found"}), 400

    player_data = extract_player_info(player_info)
    player_data.update({"status": "success", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return jsonify(player_data)

@app.route('/token', methods=['GET'])
def oauth_guest():
    """Get token using UID and password - FIXED"""
    uid = request.args.get('uid')
    password = request.args.get('password')
    
    if not uid or not password:
        return jsonify({"message": "Missing uid or password"}), 400

    token, error = get_token_from_uid_password(uid, password)
    if error:
        return jsonify({"message": error}), 400
        
    # Verify the token is valid
    author_uid = decode_author_uid(token)
    if not author_uid:
        return jsonify({"message": "Generated token is invalid"}), 400
        
    return jsonify({
        "status": "success",
        "token": token,
        "uid": uid,
        "author_uid": author_uid
    })

@app.route("/", methods=["GET"])
def home_route():

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FF INFO API</title>
        <style>
            body {
                font-family: Arial;
                background: #0f0f0f;
                color: white;
                text-align: center;
                padding: 40px;
            }
            .box {
                background: #1c1c1c;
                padding: 20px;
                border-radius: 10px;
                display: inline-block;
                text-align: left;
                max-width: 700px;
            }
            code {
                background: #333;
                padding: 3px 6px;
                border-radius: 5px;
            }
            h1 {
                color: #00ffcc;
            }
            .endpoint {
                margin-top: 15px;
                padding: 10px;
                background: #2a2a2a;
                border-radius: 8px;
            }
        </style>
    </head>
    <body>

        <h1>🔥 FF PLAYER INFO API</h1>

        <div class="box">

            <p><b>Region:</b> IND - INDIA</p>
            <p><b>Status:</b> ACTIVE</p>
            <p><b>Developer:</b> @FFDEVILX</p>

            <hr>

            <h3>📡 Endpoint</h3>

            <div class="endpoint">
                <b>/player_info</b><br><br>

                <b>Method:</b> GET<br><br>

                <b>Parameters:</b><br>
                <code>uid</code> - your account UID<br>
                <code>password</code> - your account password<br>
                <code>friend_uid</code> - target player UID<br><br>

                <b>Example:</b><br>
                <code>
                /player_info?uid=YOUR_UID&password=YOUR_PASSWORD&friend_uid=TARGET_UID
                </code>
            </div>

            <hr>

            <h3>⚡ Health Check</h3>
            <div class="endpoint">
                <code>/health</code>
            </div>

        </div>

    </body>
    </html>
    """

    return html

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "FreeFire-API"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)