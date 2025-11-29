#!/usr/bin/env python3
"""
Instagram Reporter Bot v5.0 ULTIMATE
Advanced Anti-Detection & Anti-Ban Protection
"""

import asyncio
import logging
import time
import random
import sqlite3
import threading
import hashlib
import uuid
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = '8400952826:AAFDIGBqFIhFjGEXMAVhBPx2DWd60QOqjyA'
OWNER_ID = 8496035093
DEVELOPER = '@RW_B2'

REPORT_TYPES = {
    '1': 'Spam', '2': 'Self Injury', '3': 'Drugs', '4': 'Nudity',
    '5': 'Violence (Type 3)', '6': 'Hate Speech', '7': 'Harassment',
    '8': 'Impersonation', '9': 'Impersonation (Biz)', '10': 'Impersonation (BMW)',
    '11': 'Under 13', '12': 'Gun Selling', '13': 'Violence (Type 1)', '14': 'Violence (Type 4)',
}

REPORT_CATEGORIES = {
    'violence': {'5': 'Violence (Type 3)', '13': 'Violence (Type 1)', '14': 'Violence (Type 4)'},
    'drugs': {'3': 'Drugs'},
    'impersonation': {'8': 'Impersonation', '9': 'Impersonation (Biz)', '10': 'Impersonation (BMW)'},
    'special': {'1': 'Spam', '2': 'Self Injury', '4': 'Nudity', '6': 'Hate Speech', '7': 'Harassment', '11': 'Under 13', '12': 'Gun Selling'},
}

CONTENT_TYPES = {
    'profile': 'Report Profile Account',
    'story': 'Report Story',
    'reel': 'Report Reels',
    'post': 'Report Post',
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

PROXIES = [
    "2.56.119.89:5074", "103.145.185.97:61416", "103.152.100.155:8080",
    "104.211.204.103:80", "104.211.31.97:80", "185.217.116.18:45554",
    "203.198.130.39:8080", "185.10.127.18:3128", "156.240.45.170:8080",
    "46.19.138.75:80", "92.242.192.99:80", "103.162.165.15:8080",
]

class RateLimiter:
    def __init__(self):
        self.request_counts = defaultdict(list)
    
    def check_rate(self, session_id: str, max_per_minute: int = 10):
        current_time = time.time()
        self.request_counts[session_id] = [t for t in self.request_counts[session_id] if current_time - t < 60]
        if len(self.request_counts[session_id]) >= max_per_minute:
            return False
        self.request_counts[session_id].append(current_time)
        return True

rate_limiter = RateLimiter()

class Database:
    def __init__(self, db_name: str = 'instagram_reporter.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            is_admin INTEGER DEFAULT 0, is_subscribed INTEGER DEFAULT 0,
            subscription_expires TEXT, added_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS access_codes (
            id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, expires_at TEXT NOT NULL,
            created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, session_id TEXT NOT NULL,
            csrf_token TEXT NOT NULL, is_valid INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_targets (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, target_username TEXT NOT NULL,
            target_id TEXT, added_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ban_log (
            id INTEGER PRIMARY KEY, user_id INTEGER, session_id TEXT,
            banned_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()
    
    def is_user_exists(self, user_id: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except:
            return False
    
    def add_user(self, user_id: int, username: str, first_name: str, added_by: int, is_subscribed: int = 0, days: int = 0) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            expires = (datetime.now() + timedelta(days=days)).isoformat() if is_subscribed else None
            cursor.execute('INSERT OR REPLACE INTO users (user_id, username, first_name, is_subscribed, subscription_expires, added_by) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, username, first_name, is_subscribed, expires, added_by))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def is_subscribed(self, user_id: int) -> bool:
        if user_id == OWNER_ID:
            return True
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT is_subscribed, subscription_expires FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            if result and result['is_subscribed']:
                expires = datetime.fromisoformat(result['subscription_expires']) if result['subscription_expires'] else None
                if expires and expires > datetime.now():
                    return True
            return False
        except:
            return False
    
    def is_admin(self, user_id: int) -> bool:
        if user_id == OWNER_ID:
            return True
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result is not None and result['is_admin'] == 1
        except:
            return False
    
    def set_admin(self, user_id: int, is_admin: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_admin = ? WHERE user_id = ?', (is_admin, user_id))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def add_access_code(self, code: str, days: int, created_by: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            expires_at = (datetime.now() + timedelta(days=days)).isoformat()
            cursor.execute('INSERT INTO access_codes (code, expires_at, created_by) VALUES (?, ?, ?)', (code, expires_at, created_by))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def verify_and_use_code(self, code: str, user_id: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM access_codes WHERE code = ? AND expires_at > ?', (code, datetime.now().isoformat()))
            if cursor.fetchone():
                self.add_user(user_id, '', '', OWNER_ID, is_subscribed=1, days=30)
                cursor.execute('DELETE FROM access_codes WHERE code = ?', (code,))
                conn.commit()
                conn.close()
                return True
            conn.close()
            return False
        except:
            return False
    
    def add_session(self, user_id: int, session_id: str, csrf_token: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO user_sessions (user_id, session_id, csrf_token) VALUES (?, ?, ?)', (user_id, session_id, csrf_token))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_sessions(self, user_id: int) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT session_id, csrf_token FROM user_sessions WHERE user_id = ? AND is_valid = 1', (user_id,))
            sessions = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return sessions
        except:
            return []
    
    def add_target(self, user_id: int, target_username: str, target_id: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO user_targets (user_id, target_username, target_id) VALUES (?, ?, ?)', (user_id, target_username, target_id))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_targets(self, user_id: int) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT target_username, target_id FROM user_targets WHERE user_id = ?', (user_id,))
            targets = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return targets
        except:
            return []
    
    def get_all_users(self) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, is_admin, is_subscribed FROM users ORDER BY created_at DESC')
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return users
        except:
            return []
    
    def get_all_codes(self) -> List[Tuple]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT code, expires_at FROM access_codes WHERE expires_at > ? ORDER BY expires_at', (datetime.now().isoformat(),))
            codes = cursor.fetchall()
            conn.close()
            return codes
        except:
            return []

db = Database()

class InstagramAPI:
    @staticmethod
    def get_random_user_agent() -> str:
        return random.choice(USER_AGENTS)
    
    @staticmethod
    def get_random_proxy() -> Optional[str]:
        if random.random() > 0.3:
            return random.choice(PROXIES)
        return None
    
    @staticmethod
    def random_delay():
        delay = random.uniform(5, 20)
        time.sleep(delay)
    
    @staticmethod
    def get_anti_detection_headers(session_id: str, csrf_token: str) -> Dict:
        return {
            'User-Agent': InstagramAPI.get_random_user_agent(),
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en;q=0.7']),
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': '*/*',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Connection': 'keep-alive',
            'Host': 'i.instagram.com',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/',
            'Cookie': f'sessionid={session_id}; Path=/; Domain=.instagram.com',
            'X-CSRFToken': csrf_token,
            'X-IG-App-ID': '936619743392459',
            'X-IG-WWW-Claim': '0',
            'X-Requested-With': 'XMLHttpRequest',
            'X-IG-Connection-Type': random.choice(['WIFI', '4g', '5g']),
            'X-IG-Connection-Speed': random.choice(['slow-2g', '2g', '3g', '4g']),
        }
    
    @staticmethod
    def validate_session(session_id: str, csrf_token: str) -> bool:
        try:
            headers = InstagramAPI.get_anti_detection_headers(session_id, csrf_token)
            proxy_url = InstagramAPI.get_random_proxy()
            proxies = {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'} if proxy_url else None
            InstagramAPI.random_delay()
            response = requests.get('https://i.instagram.com/api/v1/accounts/current_user/', headers=headers, proxies=proxies, timeout=10, allow_redirects=False)
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def get_user_id(target: str) -> Optional[str]:
        try:
            target_clean = target.lower().replace('@', '').strip()
            for attempt in range(3):
                try:
                    headers = {'User-Agent': InstagramAPI.get_random_user_agent(), 'Accept-Language': 'en-US,en;q=0.9', 'Accept-Encoding': 'gzip, deflate', 'Connection': 'keep-alive'}
                    proxy_url = InstagramAPI.get_random_proxy()
                    proxies = {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'} if proxy_url else None
                    InstagramAPI.random_delay()
                    response = requests.post('https://i.instagram.com/api/v1/users/lookup/', headers=headers, data={'signed_body': f'35a2d547d3b6ff400f713948cdffe0b789a903f86117eb6e2f3e573079b2f038.{{"q":"{target_clean}"}}'}, proxies=proxies, timeout=10, allow_redirects=False)
                    if response.status_code == 200:
                        data = response.json()
                        if 'user_id' in data:
                            return str(data['user_id'])
                except:
                    if attempt < 2:
                        time.sleep(random.uniform(3, 8))
                    continue
            return None
        except:
            return None
    
    @staticmethod
    def send_report(target_id: str, session_id: str, csrf_token: str, reason: str, content_type: str = 'profile') -> Tuple[bool, int, str]:
        try:
            if not rate_limiter.check_rate(session_id):
                return False, 429, "Rate limited"
            InstagramAPI.random_delay()
            headers = InstagramAPI.get_anti_detection_headers(session_id, csrf_token)
            if content_type == 'post':
                endpoint = f"https://i.instagram.com/media/{target_id}/flag/"
            elif content_type == 'story':
                endpoint = f"https://i.instagram.com/stories/{target_id}/flag/"
            elif content_type == 'reel':
                endpoint = f"https://i.instagram.com/clips/{target_id}/flag/"
            else:
                endpoint = f"https://i.instagram.com/users/{target_id}/flag/"
            proxy_url = InstagramAPI.get_random_proxy()
            proxies = {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'} if proxy_url else None
            response = requests.post(endpoint, headers=headers, data=f'source_name=&reason_id={reason}&frx_context=', proxies=proxies, allow_redirects=False, timeout=15, verify=False)
            status = response.status_code
            if status == 429:
                return False, 429, "ACCOUNT FLAGGED - BAN DETECTED"
            elif status == 500:
                return False, 500, "Target not found"
            elif status in [200, 302]:
                return True, status, "Success"
            elif status == 401 or status == 403:
                return False, status, "Invalid session"
            else:
                return False, status, f"Error {status}"
        except Exception as e:
            return False, 0, str(e)

class TelegramBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or 'NoUsername'
            first_name = update.effective_user.first_name or 'User'
            if not db.is_user_exists(user_id):
                db.add_user(user_id, username, first_name, OWNER_ID)
            if user_id == OWNER_ID:
                await self.show_owner_menu(update, context)
            elif db.is_admin(user_id):
                await self.show_admin_menu(update, context)
            elif db.is_subscribed(user_id):
                await self.show_user_menu(update, context)
            else:
                context.user_data['state'] = 'waiting_subscription'
                await update.message.reply_text(f"Welcome! Need subscription.\n\nDeveloper: {DEVELOPER}\n\nSend access code or ask admin.")
        except:
            pass
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            text = f"""All Report Types:
1=Spam 2=Self Injury 3=Drugs 4=Nudity
5=Violence(3) 6=Hate 7=Harassment
8=Impersonation 9=Impersonation(Biz) 10=Impersonation(BMW)
11=Under13 12=Gun 13=Violence(1) 14=Violence(4)

Developer: {DEVELOPER}"""
            await update.message.reply_text(text)
        except:
            pass
    
    async def show_owner_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[InlineKeyboardButton("Add Admin", callback_data='owner_add_admin')], [InlineKeyboardButton("View Users", callback_data='owner_view_users')], [InlineKeyboardButton("Create Code", callback_data='owner_create_code')], [InlineKeyboardButton("View Codes", callback_data='owner_view_codes')], [InlineKeyboardButton("Start Reporting", callback_data='start_reporting')]]
        text = f"OWNER PANEL\n\nDeveloper: {DEVELOPER}"
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[InlineKeyboardButton("Add User", callback_data='admin_add_user')], [InlineKeyboardButton("Create Code", callback_data='admin_create_code')], [InlineKeyboardButton("Start Reporting", callback_data='start_reporting')]]
        text = "ADMIN PANEL"
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[InlineKeyboardButton("Add Sessions", callback_data='add_sessions')], [InlineKeyboardButton("Add Targets", callback_data='add_targets')], [InlineKeyboardButton("Start Reporting", callback_data='start_reporting')]]
        text = "INSTAGRAM REPORTER"
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()
            user_id = update.effective_user.id
            callback = query.data
            if callback == 'owner_add_admin':
                context.user_data['state'] = 'owner_add_admin'
                await query.edit_message_text("Enter user ID:")
            elif callback == 'owner_view_users':
                users = db.get_all_users()
                text = "Users:\n\n"
                for u in users[:10]:
                    text += f"- {u['user_id']} ({u['username']})\n"
                await query.edit_message_text(text)
            elif callback == 'owner_create_code':
                context.user_data['state'] = 'owner_create_code'
                await query.edit_message_text("Format: CODE,DAYS\nExample: ABC123,30")
            elif callback == 'owner_view_codes':
                codes = db.get_all_codes()
                text = "Active Codes:\n\n"
                for code, exp in codes[:5]:
                    text += f"- {code}\n"
                await query.edit_message_text(text)
            elif callback == 'admin_add_user':
                context.user_data['state'] = 'admin_add_user'
                await query.edit_message_text("Enter user ID:")
            elif callback == 'admin_create_code':
                context.user_data['state'] = 'admin_create_code'
                await query.edit_message_text("Format: CODE,DAYS")
            elif callback == 'add_sessions':
                context.user_data['state'] = 'add_session'
                keyboard = [[InlineKeyboardButton("Single", callback_data='single_session')], [InlineKeyboardButton("Multi", callback_data='multi_session')]]
                await query.edit_message_text("Select mode:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif callback == 'single_session':
                context.user_data['session_mode'] = 'single'
                context.user_data['state'] = 'input_session'
                await query.edit_message_text("Send: sessionid:csrftoken")
            elif callback == 'multi_session':
                context.user_data['session_mode'] = 'multi'
                context.user_data['state'] = 'input_session'
                await query.edit_message_text("Send sessions (new line each)")
            elif callback == 'add_targets':
                context.user_data['state'] = 'add_target'
                keyboard = [[InlineKeyboardButton("Single", callback_data='single_target')], [InlineKeyboardButton("Multi", callback_data='multi_target')]]
                await query.edit_message_text("Select mode:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif callback == 'single_target':
                context.user_data['target_mode'] = 'single'
                context.user_data['state'] = 'input_target'
                await query.edit_message_text("Send: @username or id:12345")
            elif callback == 'multi_target':
                context.user_data['target_mode'] = 'multi'
                context.user_data['state'] = 'input_target'
                await query.edit_message_text("Send targets: user1:user2:user3")
            elif callback == 'start_reporting':
                await self.choose_content_type(update, context)
            elif callback.startswith('content_'):
                content_type = callback.replace('content_', '')
                context.user_data['content_type'] = content_type
                if content_type == 'profile':
                    await self.choose_report_mode(update, context)
                else:
                    buttons = [[InlineKeyboardButton("All", callback_data=f'report_all_{content_type}')], [InlineKeyboardButton("Single", callback_data=f'report_single_{content_type}')]]
                    await query.edit_message_text("Mode:", reply_markup=InlineKeyboardMarkup(buttons))
            elif callback.startswith('report_all_'):
                content_type = callback.replace('report_all_', '')
                context.user_data['content_type'] = content_type
                context.user_data['report_mode'] = 'all'
                await self.choose_report_mode(update, context)
            elif callback.startswith('report_single_'):
                content_type = callback.replace('report_single_', '')
                context.user_data['content_type'] = content_type
                context.user_data['report_mode'] = 'single'
                context.user_data['state'] = 'input_item_id'
                await query.edit_message_text(f"Send {content_type} ID")
            elif callback.startswith('mode_'):
                mode = callback.replace('mode_', '')
                context.user_data['report_type'] = mode
                if mode == 'normal':
                    await self.show_report_categories(update, context)
                else:
                    await self.show_advanced_mode(update, context)
            elif callback.startswith('category_'):
                category = callback.replace('category_', '')
                buttons = []
                if category in REPORT_CATEGORIES:
                    for type_key, type_name in REPORT_CATEGORIES[category].items():
                        buttons.append([InlineKeyboardButton(f"{type_key}-{type_name}", callback_data=f'type_{type_key}')])
                await query.edit_message_text("Type:", reply_markup=InlineKeyboardMarkup(buttons))
            elif callback.startswith('type_'):
                reason = callback.replace('type_', '')
                context.user_data['reason'] = reason
                await self.start_reporting(update, context)
        except:
            pass
    
    async def choose_content_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        buttons = [[InlineKeyboardButton("Report Profile", callback_data='content_profile')], [InlineKeyboardButton("Report Story", callback_data='content_story')], [InlineKeyboardButton("Report Reels", callback_data='content_reel')], [InlineKeyboardButton("Report Post", callback_data='content_post')]]
        await update.callback_query.edit_message_text("Type:", reply_markup=InlineKeyboardMarkup(buttons))
    
    async def choose_report_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        buttons = [[InlineKeyboardButton("Normal", callback_data='mode_normal')], [InlineKeyboardButton("Advanced", callback_data='mode_advanced')]]
        await update.callback_query.edit_message_text("Mode:", reply_markup=InlineKeyboardMarkup(buttons))
    
    async def show_report_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        buttons = [[InlineKeyboardButton("Violence", callback_data='category_violence'), InlineKeyboardButton("Drugs", callback_data='category_drugs')], [InlineKeyboardButton("Impersonation", callback_data='category_impersonation'), InlineKeyboardButton("Special", callback_data='category_special')]]
        await update.callback_query.edit_message_text("Category:", reply_markup=InlineKeyboardMarkup(buttons))
    
    async def show_advanced_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['state'] = 'input_advanced'
        text = "Advanced:\n\n"
        for k, v in REPORT_TYPES.items():
            text += f"{k}={v}\n"
        text += "\nSend: 1-6-7-4"
        await update.callback_query.edit_message_text(text)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            message = update.message.text.strip()
            state = context.user_data.get('state', 'idle')
            if state == 'owner_add_admin':
                try:
                    admin_id = int(message)
                    db.set_admin(admin_id, 1)
                    await update.message.reply_text(f"Admin added: {admin_id}")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Error!")
            elif state == 'owner_create_code':
                if ',' not in message:
                    await update.message.reply_text("Format: CODE,DAYS")
                    return
                parts = message.split(',')
                code = parts[0].strip().upper()
                try:
                    days = int(parts[1].strip())
                    if db.add_access_code(code, days, user_id):
                        await update.message.reply_text(f"Created: {code}")
                        context.user_data['state'] = 'idle'
                    else:
                        await update.message.reply_text("Error!")
                except:
                    await update.message.reply_text("Invalid!")
            elif state == 'admin_add_user':
                try:
                    target_id = int(message.replace('@', '').strip())
                    db.add_user(target_id, '', '', user_id, is_subscribed=1, days=30)
                    await update.message.reply_text(f"Added: {target_id}")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid!")
            elif state == 'admin_create_code':
                if ',' not in message:
                    await update.message.reply_text("Format: CODE,DAYS")
                    return
                parts = message.split(',')
                code = parts[0].strip().upper()
                try:
                    days = int(parts[1].strip())
                    if db.add_access_code(code, days, user_id):
                        await update.message.reply_text(f"Created: {code}")
                        context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid!")
            elif state == 'input_session':
                sessions = message.split('\n') if context.user_data.get('session_mode') == 'multi' else [message]
                valid = 0
                for s in sessions:
                    s = s.strip()
                    if ':' not in s:
                        continue
                    parts = s.split(':')
                    if len(parts) != 2:
                        continue
                    session_id, csrf = parts[0].strip(), parts[1].strip()
                    if len(session_id) > 20 and len(csrf) > 20:
                        if InstagramAPI.validate_session(session_id, csrf):
                            db.add_session(user_id, session_id, csrf)
                            valid += 1
                await update.message.reply_text(f"Added: {valid}")
                context.user_data['state'] = 'idle'
            elif state == 'input_target':
                targets = message.split(':') if ':' in message else (message.split() if ' ' in message else message.split('\n'))
                valid = 0
                for target in targets:
                    target = target.lower().replace('@', '').strip()
                    if target:
                        target_id = InstagramAPI.get_user_id(target)
                        if target_id:
                            db.add_target(user_id, target, target_id)
                            valid += 1
                await update.message.reply_text(f"Added: {valid}")
                context.user_data['state'] = 'idle'
            elif state == 'input_item_id':
                context.user_data['item_id'] = message.strip().split('/')[-1]
                context.user_data['state'] = 'idle'
                buttons = [[InlineKeyboardButton("Normal", callback_data='mode_normal')], [InlineKeyboardButton("Advanced", callback_data='mode_advanced')]]
                await update.message.reply_text("Mode:", reply_markup=InlineKeyboardMarkup(buttons))
            elif state == 'input_advanced':
                reasons = [r.strip() for r in message.split('-') if r.strip()]
                context.user_data['reasons'] = reasons
                sessions = db.get_sessions(user_id)
                targets = db.get_targets(user_id)
                if not sessions or not targets:
                    await update.message.reply_text("Add sessions/targets!")
                    return
                status_msg = await context.bot.send_message(user_id, f"Starting...\nSessions: {len(sessions)}\nTargets: {len(targets)}\nTypes: {len(reasons)}")
                threading.Thread(target=self.reporting_loop_advanced, args=(user_id, sessions, targets, reasons, context.user_data.get('content_type', 'profile'), status_msg.message_id, context.bot), daemon=True).start()
            elif state == 'waiting_subscription':
                if db.verify_and_use_code(message, user_id):
                    await update.message.reply_text("Access granted!")
                    context.user_data['state'] = 'idle'
                    await self.show_user_menu(update, context)
                else:
                    await update.message.reply_text("Invalid!")
        except:
            pass
    
    async def start_reporting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            sessions = db.get_sessions(user_id)
            targets = db.get_targets(user_id)
            reason = context.user_data.get('reason', '1')
            content_type = context.user_data.get('content_type', 'profile')
            if not sessions or not targets:
                await query.edit_message_text("Add sessions/targets!")
                return
            status_msg = await context.bot.send_message(user_id, f"Starting\n\nSessions: {len(sessions)}\nTargets: {len(targets)}\nReason: {reason}\n\nStatus: Initializing...")
            threading.Thread(target=self.reporting_loop, args=(user_id, sessions, targets, reason, content_type, status_msg.message_id, context.bot), daemon=True).start()
        except:
            pass
    
    def reporting_loop(self, user_id: int, sessions: List[Dict], targets: List[Dict], reason: str, content_type: str, status_msg_id: int, bot):
        try:
            done = 0
            failed = 0
            for target in targets:
                for session in sessions:
                    success, status, msg = InstagramAPI.send_report(target['target_id'], session['session_id'], session['csrf_token'], reason, content_type)
                    if success:
                        done += 1
                    else:
                        failed += 1
                        if status == 429:
                            asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"ACCOUNT BANNED!\n\nDone: {done}\nFailed: {failed}\n\nSTOP ALL ACTIVITY!"))
                            return
                    if (done + failed) % 3 == 0:
                        try:
                            asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"Done: {done} | Failed: {failed} | Target: @{target['target_username']}"))
                        except:
                            pass
            asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"Complete!\n\nDone: {done}\nFailed: {failed}\nTotal: {done + failed}"))
        except:
            pass
    
    def reporting_loop_advanced(self, user_id: int, sessions: List[Dict], targets: List[Dict], reasons: List, content_type: str, status_msg_id: int, bot):
        try:
            done = 0
            failed = 0
            for target in targets:
                for reason in reasons:
                    for session in sessions:
                        success, status, msg = InstagramAPI.send_report(target['target_id'], session['session_id'], session['csrf_token'], reason, content_type)
                        if success:
                            done += 1
                        else:
                            failed += 1
                            if status == 429:
                                asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"BANNED!\n\nDone: {done}"))
                                return
                        if (done + failed) % 3 == 0:
                            try:
                                asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"Advanced: {done} | Failed: {failed}"))
                            except:
                                pass
            asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"Advanced Done!\n\nDone: {done}\nFailed: {failed}"))
        except:
            pass
    
    def run(self):
        logger.info("Bot starting...")
        self.app.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
