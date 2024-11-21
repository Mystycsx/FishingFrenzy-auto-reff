import requests
import random
import string
import time
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
import os
import uuid  # Untuk generate deviceId unik
import json

# Muat variabel lingkungan dari file .env
load_dotenv()

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ambil data sensitif dari .env
API_URL = os.getenv("API_URL")
PRIVY_APP_ID = os.getenv("PRIVY_APP_ID")
PRIVY_CA_ID = os.getenv("PRIVY_CA_ID")
PROXY_URL = os.getenv("PROXY_URL")  # URL proxy, misalnya "http://username:password@proxy_address:port"

# Konfigurasi proxy
proxies = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

# Output file
OUTPUT_FOLDER = "fishingF"
OUTPUT_FILE = "accounts.json"

# Fungsi untuk menghasilkan device ID acak
def generate_device_id():
    return str(uuid.uuid4())

# Fungsi untuk menghasilkan username acak
def generate_random_username():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

# Fungsi untuk login sebagai tamu dan mendapatkan token akses serta userId
def guest_login(device_id):
    url = f"{API_URL}/v1/auth/guest-login"
    headers = {"Content-Type": "application/json"}
    data = {"deviceId": device_id, "teleUserId": None, "teleName": None}
    try:
        response = requests.post(url, json=data, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        json_response = response.json()
        token = json_response["tokens"]["access"]["token"]
        user_id = json_response["user"]["id"]  # Ambil userId
        logging.info(f"Access Token and User ID obtained for Device ID: {device_id}")
        return token, user_id
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during guest login: {e}")
        return None, None

# Fungsi untuk memverifikasi kode referensi
def verify_reference_code(access_token, username, koderef):
    url = f"{API_URL}/v1/reference-code/verify?code={koderef}"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={}, headers=headers, proxies=proxies, timeout=10)
        if response.status_code == 200:
            logging.info(f"Code {koderef} verified successfully for user {username}.")
            return True
        else:
            logging.warning(f"Verification failed for user {username}. Status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Error verifying user {username}: {e}")
        return False

# Fungsi untuk mencatat event analytics
def log_analytics_event(access_token, event_name):
    url = "https://auth.privy.io/api/v1/analytics_events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Privy-Client": "react-auth:1.88.4",
        "Privy-App-Id": PRIVY_APP_ID,
        "Privy-Ca-Id": PRIVY_CA_ID,
        "Origin": "https://fishingfrenzy.co",
    }
    data = {
        "event_name": event_name,
        "client_id": PRIVY_CA_ID,
        "payload": {
            "embeddedWallets": {
                "createOnLogin": "all-users",
                "noPromptOnSignature": True,
                "waitForTransactionConfirmation": True,
                "priceDisplay": {"primary": "native-token", "secondary": None},
            },
            "supportedChains": [1, 8453],
            "defaultChain": 8453,
            "clientTimestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    try:
        response = requests.post(url, json=data, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        logging.info(f"Event '{event_name}' logged successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error logging event: {e}")

# Fungsi untuk menyimpan token dan userId ke file JSON
def save_user_data_to_file(token, user_id):
    # Buat folder jika belum ada
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    file_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)

    # Baca data sebelumnya jika file sudah ada
    user_data = []
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            try:
                user_data = json.load(file)
            except json.JSONDecodeError:
                logging.warning(f"{OUTPUT_FILE} is empty or invalid. Overwriting file.")

    # Tambahkan token dan userId baru
    user_data.append({"access_token": f"Bearer {token}", "user_id": user_id})

    # Tulis ke file
    with open(file_path, "w") as file:
        json.dump(user_data, file, indent=4)
    logging.info(f"User data saved to {file_path}")

# Fungsi utama untuk membuat dan memverifikasi pengguna serta mencatat event
def automate_user_creation(num_users, koderef):
    for i in range(num_users):
        device_id = generate_device_id()  # Buat device ID unik untuk setiap pengguna
        username = generate_random_username()  # Buat username acak
        logging.info(f"Creating user {i + 1}: {username} with Device ID: {device_id}")
        
        access_token, user_id = guest_login(device_id)  # Login dengan device ID unik
        if access_token and user_id:
            save_user_data_to_file(access_token, user_id)  # Simpan token dan userId ke file
            if verify_reference_code(access_token, username, koderef):
                log_analytics_event(access_token, "sdk_initialize")
        time.sleep(random.uniform(1, 3))  # Jeda acak untuk menghindari rate limiting

# Eksekusi program
if __name__ == "__main__":
    try:
        num_users_to_create = int(input("Enter the number of users to create: "))  # Jumlah akun yang ingin dibuat
        koderef = input("Enter the reference code: ")
        automate_user_creation(num_users_to_create, koderef)
    except ValueError:
        logging.error("Invalid input. Please enter a valid number.")
