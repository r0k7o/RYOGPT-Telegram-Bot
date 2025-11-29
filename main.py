#!/usr/bin/env python3
import asyncio
import logging
import time
import random
import sqlite3
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = '8400952826:AAFDIGBqFIhFjGEXMAVhBPx2DWd60QOqjyA'
OWNER_ID = 8496035093
DEVELOPER_USERNAME = 'RW_B2'

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1",
]

PROXIES = [
    "2.56.119.89:5074", "103.145.185.97:61416", "103.152.100.155:8080",
    "104.211.204.103:80", "104.211.31.97:80", "185.217.116.18:45554",
    "203.198.130.39:8080", "185.10.127.18:3128", "156.240.45.170:8080",
    "46.19.138.75:80", "92.242.192.99:80", "103.162.165.15:8080",
]

IMPERSONATION_TARGETS = {
    'meta': ['Facebook Official', 'Instagram Official', 'WhatsApp Official', 'Threads Official', 'Meta Platforms'],
    'apple': ['Apple Official', 'Apple Support', 'iTunes Official', 'Apple TV', 'App Store'],
    'google': ['Google Official', 'Gmail Official', 'YouTube Official', 'Chrome Official', 'Google Play'],
    'amazon': ['Amazon Official', 'Amazon Prime', 'AWS Official', 'Amazon Music', 'Amazon Books'],
    'microsoft': ['Microsoft Official', 'Xbox Official', 'Windows Official', 'Outlook Official', 'Office 365'],
    'netflix': ['Netflix Official', 'Netflix Support', 'Netflix Films', 'Netflix Series'],
    'twitter': ['Twitter Official', 'Twitter Support', 'Twitter Safety', 'Twitter Developer'],
    'tesla': ['Tesla Official', 'Elon Musk Verified', 'Tesla Energy', 'Tesla Service'],
    'nike': ['Nike Official', 'Nike Store', 'Nike Support', 'Nike Sports'],
    'adidas': ['Adidas Official', 'Adidas Store', 'Adidas Support', 'Adidas Sports'],
    'crypto': ['Bitcoin Official', 'Ethereum Official', 'Coinbase Official', 'Binance Official'],
    'gaming': ['PlayStation Official', 'Xbox Official', 'Nintendo Official', 'Steam Official'],
}

REPORT_CATEGORIES_FULL = {
    'violence': {
        '5': 'Violence', '13': 'Violence', '14': 'Violence Threat', 
        '32': 'Dangerous or Harmful Acts', '25': 'Abuse of Animals'
    },
    'drugs': {
        '3': 'Drugs', '17': 'Dangerous Content'
    },
    'sexual': {
        '4': 'Sexual Content', '27': 'Sexual Exploitation', '26': 'Child Safety'
    },
    'impersonation': {
        '8': 'Impersonation', '9': 'Impersonation', '10': 'Impersonation'
    },
    'harassment': {
        '6': 'Hate Speech', '7': 'Harassment', '29': 'Hate Speech', 
        '30': 'Bullying', '31': 'Doxxing'
    },
    'abuse': {
        '15': 'Self-Injury Content', '2': 'Self-Injury', '33': 'Self-Harm Content', '34': 'Eating Disorder Content'
    },
    'misinformation': {
        '16': 'Misinformation', '22': 'False Information', '21': 'Scam'
    },
    'spam': {
        '1': 'Spam', '19': 'Spam', '20': 'Inauthentic Activity'
    },
    'intellectual': {
        '18': 'Intellectual Property', '23': 'Copyright Infringement', 
        '24': 'Counterfeit Goods'
    },
    'illegal': {
        '28': 'Illegal Activity', '12': 'Illegal Sale of Goods', '11': 'Minor Safety Concern'
    }
}

REPORT_TYPES = {
    '1': 'Spam', '2': 'Self-Injury', '3': 'Drugs', '4': 'Sexual Content',
    '5': 'Violence', '6': 'Hate Speech', '7': 'Harassment',
    '8': 'Impersonation', '9': 'Impersonation', '10': 'Impersonation',
    '11': 'Minor Safety Concern', '12': 'Illegal Sale of Goods', '13': 'Violence', '14': 'Violence Threat',
    '15': 'Self-Injury Content', '16': 'Misinformation', '17': 'Dangerous Content', '18': 'Intellectual Property',
    '19': 'Spam', '20': 'Inauthentic Activity', '21': 'Scam', '22': 'False Information',
    '23': 'Copyright Infringement', '24': 'Counterfeit Goods', '25': 'Abuse of Animals', '26': 'Child Safety',
    '27': 'Sexual Exploitation', '28': 'Illegal Activity', '29': 'Hate Speech', '30': 'Bullying',
    '31': 'Doxxing', '32': 'Dangerous or Harmful Acts', '33': 'Self-Harm Content', '34': 'Eating Disorder Content',
}

class Database:
    def __init__(self, db_name: str = 'reporter_pro.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, role TEXT DEFAULT user, subscription_expires TEXT, subscription_days INTEGER DEFAULT 0, added_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS access_codes (id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, expires_at TEXT NOT NULL, created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS user_sessions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, session_id TEXT NOT NULL, is_valid INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS user_targets (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, target_username TEXT NOT NULL, target_id TEXT, added_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS admin_settings (id INTEGER PRIMARY KEY, setting_key TEXT UNIQUE, setting_value TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)')
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
    
    def add_user(self, user_id: int, username: str, first_name: str, role: str = 'user', added_by: int = None, days: int = 30) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            expires = (datetime.now() + timedelta(days=days)).isoformat() if role == 'user' else None
            cursor.execute('INSERT OR REPLACE INTO users (user_id, username, first_name, role, subscription_expires, subscription_days, added_by) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (user_id, username, first_name, role, expires, days, added_by or OWNER_ID))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_user_role(self, user_id: int) -> str:
        if user_id == OWNER_ID:
            return 'owner'
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT role, subscription_expires FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                role, expires = result['role'], result['subscription_expires']
                if role == 'user' and expires:
                    if datetime.fromisoformat(expires) < datetime.now():
                        return 'expired'
                return role
            return 'none'
        except:
            return 'none'
    
    def get_user_info(self, user_id: int) -> Dict:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, role, subscription_expires, subscription_days FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else {}
        except:
            return {}
    
    def set_user_role(self, user_id: int, new_role: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE user_id = ?', (new_role, user_id))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def set_user_subscription(self, user_id: int, days: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            expires = (datetime.now() + timedelta(days=days)).isoformat()
            cursor.execute('UPDATE users SET subscription_expires = ?, subscription_days = ? WHERE user_id = ?', (expires, days, user_id))
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
                self.add_user(user_id, '', '', 'user')
                cursor.execute('DELETE FROM access_codes WHERE code = ?', (code,))
                conn.commit()
                conn.close()
                return True
            conn.close()
            return False
        except:
            return False
    
    def get_all_users(self) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, role, subscription_expires FROM users ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def add_session(self, user_id: int, session_id: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO user_sessions (user_id, session_id) VALUES (?, ?)', (user_id, session_id))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_sessions(self, user_id: int) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT session_id FROM user_sessions WHERE user_id = ? AND is_valid = 1', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
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
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def get_access_codes(self) -> List:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT code, expires_at FROM access_codes WHERE expires_at > ? ORDER BY expires_at', (datetime.now().isoformat(),))
            return cursor.fetchall()
        except:
            return []
    
    def cleanup_expired_users(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE role = ? AND subscription_expires < ?', 
                ('expired', 'user', datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except:
            pass

db = Database()

class InstagramAPI:
    @staticmethod
    def get_random_user_agent() -> str:
        return random.choice(USER_AGENTS)
    
    @staticmethod
    def get_random_proxy() -> Optional[str]:
        return random.choice(PROXIES) if random.random() > 0.3 else None
    
    @staticmethod
    def random_delay():
        time.sleep(random.uniform(5, 20))
    
    @staticmethod
    def get_headers(session_id: str) -> Dict:
        return {
            'User-Agent': InstagramAPI.get_random_user_agent(),
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8']),
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': '*/*',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Connection': 'keep-alive',
            'Host': 'i.instagram.com',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/',
            'Cookie': f'sessionid={session_id}',
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest',
            'X-IG-Connection-Type': random.choice(['WIFI', '4g', '5g']),
        }
    
    @staticmethod
    def validate_session(session_id: str) -> bool:
        try:
            InstagramAPI.random_delay()
            headers = InstagramAPI.get_headers(session_id)
            proxy_url = InstagramAPI.get_random_proxy()
            proxies = {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'} if proxy_url else None
            response = requests.get('https://i.instagram.com/api/v1/accounts/current_user/', headers=headers, proxies=proxies, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def get_user_id(target: str) -> Optional[str]:
        try:
            target_clean = target.lower().replace('@', '').strip()
            for attempt in range(3):
                try:
                    InstagramAPI.random_delay()
                    headers = {'User-Agent': InstagramAPI.get_random_user_agent(), 'Accept-Language': 'en-US,en;q=0.9', 'Connection': 'keep-alive'}
                    proxy_url = InstagramAPI.get_random_proxy()
                    proxies = {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'} if proxy_url else None
                    response = requests.post('https://i.instagram.com/api/v1/users/lookup/', headers=headers, 
                        data={'signed_body': f'35a2d547d3b6ff400f713948cdffe0b789a903f86117eb6e2f3e573079b2f038.{{"q":"{target_clean}"}}'}, 
                        proxies=proxies, timeout=10)
                    if response.status_code == 200 and 'user_id' in response.json():
                        return str(response.json()['user_id'])
                except:
                    if attempt < 2:
                        time.sleep(random.uniform(3, 8))
            return None
        except:
            return None
    
    @staticmethod
    def send_report(target_id: str, session_id: str, reason: str, content_type: str = 'profile') -> Tuple[bool, int, str]:
        try:
            InstagramAPI.random_delay()
            headers = InstagramAPI.get_headers(session_id)
            endpoints = {
                'post': f'https://i.instagram.com/media/{target_id}/flag/',
                'story': f'https://i.instagram.com/stories/{target_id}/flag/',
                'reel': f'https://i.instagram.com/clips/{target_id}/flag/',
                'profile': f'https://i.instagram.com/users/{target_id}/flag/',
            }
            endpoint = endpoints.get(content_type, endpoints['profile'])
            proxy_url = InstagramAPI.get_random_proxy()
            proxies = {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'} if proxy_url else None
            response = requests.post(endpoint, headers=headers, data=f'source_name=&reason_id={reason}&frx_context=', proxies=proxies, timeout=15, verify=False)
            if response.status_code in [200, 302]:
                return True, 200, 'Success'
            elif response.status_code == 429:
                return False, 429, 'Account Banned'
            elif response.status_code == 500:
                return False, 500, 'Target Not Found'
            else:
                return False, response.status_code, f'Error {response.status_code}'
        except Exception as e:
            return False, 0, str(e)

class TelegramBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        self.cleanup_thread = threading.Thread(target=self.cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        self.stop_flag = {}
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
    
    def cleanup_loop(self):
        while True:
            time.sleep(3600)
            db.cleanup_expired_users()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or 'NoUsername'
            first_name = update.effective_user.first_name or 'User'
            if not db.is_user_exists(user_id):
                db.add_user(user_id, username, first_name, 'user')
            role = db.get_user_role(user_id)
            if role == 'owner':
                await self.show_owner_menu(update, context)
            elif role == 'admin':
                await self.show_admin_menu(update, context)
            elif role == 'user':
                await self.show_user_menu(update, context)
            else:
                context.user_data['state'] = 'waiting_code'
                await update.message.reply_text(f"Welcome to Instagram Reporter\n\nYou need subscription to access this bot.\n\nAsk administrator for access code.\n\nDeveloper: @{DEVELOPER_USERNAME}")
        except:
            pass
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""Report Categories Available:

Violence | Sexual Content | Impersonation
Harassment | Abuse | Misinformation
Spam | Intellectual Property | Illegal

34 Report Types Total

Developer: @{DEVELOPER_USERNAME}"""
        await update.message.reply_text(text)
    
    async def show_owner_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Dashboard", callback_data='owner_dashboard')],
            [InlineKeyboardButton("User Management", callback_data='owner_users')],
            [InlineKeyboardButton("Admin Control", callback_data='owner_admins')],
            [InlineKeyboardButton("Access Codes", callback_data='owner_codes')],
            [InlineKeyboardButton("Broadcast Message", callback_data='owner_broadcast')],
            [InlineKeyboardButton("Start Reporting", callback_data='start_report')],
        ]
        text = "OWNER CONTROL PANEL\n\nFull Administrative Access"
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_owner_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users = db.get_all_users()
        total_users = len(users)
        admins = len([u for u in users if u['role'] == 'admin'])
        expired = len([u for u in users if u['role'] == 'expired'])
        
        text = f"""OWNER DASHBOARD

Total Users: {total_users}
Active Admins: {admins}
Expired Subscriptions: {expired}

Quick Actions:
"""
        keyboard = [
            [InlineKeyboardButton("Add User Subscription", callback_data='dash_add_sub')],
            [InlineKeyboardButton("Remove User", callback_data='dash_remove_user')],
            [InlineKeyboardButton("Send Message", callback_data='dash_send_msg')],
            [InlineKeyboardButton("View Stats", callback_data='dash_stats')],
            [InlineKeyboardButton("Back", callback_data='back_owner')],
        ]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Add User", callback_data='admin_add_user')],
            [InlineKeyboardButton("Create Code", callback_data='admin_create_code')],
            [InlineKeyboardButton("Send Message", callback_data='admin_send_msg')],
            [InlineKeyboardButton("Start Reporting", callback_data='start_report')],
        ]
        text = "ADMIN PANEL\n\nAdministration Tools"
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Add Sessions", callback_data='user_sessions')],
            [InlineKeyboardButton("Add Targets", callback_data='user_targets')],
            [InlineKeyboardButton("Start Reporting", callback_data='start_report')],
        ]
        text = "INSTAGRAM REPORTER\n\nManage your accounts and targets"
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
            
            if callback == 'owner_dashboard':
                await self.show_owner_dashboard(update, context)
            
            elif callback == 'back_owner':
                await self.show_owner_menu(update, context)
            
            elif callback == 'dash_add_sub':
                context.user_data['state'] = 'dash_add_sub_id'
                await query.edit_message_text("Enter user ID to add subscription:")
            
            elif callback == 'dash_remove_user':
                context.user_data['state'] = 'dash_remove_user_id'
                await query.edit_message_text("Enter user ID to remove:")
            
            elif callback == 'dash_send_msg':
                context.user_data['state'] = 'dash_send_to_user_id'
                await query.edit_message_text("Enter user ID to send message (or ALL for all users):")
            
            elif callback == 'dash_stats':
                users = db.get_all_users()
                active = len([u for u in users if u['role'] == 'user'])
                admins = len([u for u in users if u['role'] == 'admin'])
                text = f"""Statistics:

Active Users: {active}
Admins: {admins}
Total: {len(users)}

System Status: Online
"""
                await query.edit_message_text(text)
            
            elif callback == 'owner_users':
                users = db.get_all_users()
                text = "User Management:\n\n"
                for u in users[:10]:
                    text += f"ID: {u['user_id']} | Role: {u['role']} | @{u['username']}\n"
                await query.edit_message_text(text)
            
            elif callback == 'owner_admins':
                context.user_data['state'] = 'owner_admin_action'
                keyboard = [[InlineKeyboardButton("Add Admin", callback_data='owner_add_admin')], [InlineKeyboardButton("Remove Admin", callback_data='owner_remove_admin')]]
                await query.edit_message_text("Admin Management:", reply_markup=InlineKeyboardMarkup(keyboard))
            
            elif callback == 'owner_add_admin':
                context.user_data['state'] = 'owner_add_admin_id'
                await query.edit_message_text("Enter user ID to make admin:")
            
            elif callback == 'owner_remove_admin':
                context.user_data['state'] = 'owner_remove_admin_id'
                await query.edit_message_text("Enter admin ID to remove (Cannot remove owner):")
            
            elif callback == 'owner_codes':
                codes = db.get_access_codes()
                text = "Active Access Codes:\n\n"
                for code, exp in codes[:10]:
                    text += f"Code: {code}\n"
                await query.edit_message_text(text)
            
            elif callback == 'owner_broadcast':
                context.user_data['state'] = 'owner_broadcast_msg'
                await query.edit_message_text("Enter broadcast message:")
            
            elif callback == 'admin_add_user':
                context.user_data['state'] = 'admin_add_user_id'
                await query.edit_message_text("Enter user ID:")
            
            elif callback == 'admin_create_code':
                context.user_data['state'] = 'admin_create_code_input'
                await query.edit_message_text("Format: CODE,DAYS\nExample: PROMO123,30")
            
            elif callback == 'admin_send_msg':
                context.user_data['state'] = 'admin_send_msg_id'
                await query.edit_message_text("Enter user ID to message:")
            
            elif callback == 'user_sessions':
                keyboard = [[InlineKeyboardButton("Single Session", callback_data='user_single_session')], [InlineKeyboardButton("Multi Sessions", callback_data='user_multi_session')]]
                await query.edit_message_text("Session Mode:", reply_markup=InlineKeyboardMarkup(keyboard))
            
            elif callback == 'user_single_session':
                context.user_data['state'] = 'input_single_session'
                context.user_data['session_mode'] = 'single'
                await query.edit_message_text("Send: sessionid")
            
            elif callback == 'user_multi_session':
                context.user_data['state'] = 'input_multi_session'
                context.user_data['session_mode'] = 'multi'
                await query.edit_message_text("Send sessions (one per line)")
            
            elif callback == 'user_targets':
                keyboard = [[InlineKeyboardButton("Single Target", callback_data='user_single_target')], [InlineKeyboardButton("Multi Targets", callback_data='user_multi_target')]]
                await query.edit_message_text("Target Mode:", reply_markup=InlineKeyboardMarkup(keyboard))
            
            elif callback == 'user_single_target':
                context.user_data['state'] = 'input_single_target'
                await query.edit_message_text("Send target: @username or userid")
            
            elif callback == 'user_multi_target':
                context.user_data['state'] = 'input_multi_target'
                await query.edit_message_text("Send targets (separated by space or line)")
            
            elif callback == 'start_report':
                sessions = db.get_sessions(user_id)
                targets = db.get_targets(user_id)
                if not sessions or not targets:
                    await query.edit_message_text("Error: Add sessions and targets first!")
                    return
                keyboard = [[InlineKeyboardButton("Profile", callback_data='report_profile')], [InlineKeyboardButton("Story", callback_data='report_story')], [InlineKeyboardButton("Reels", callback_data='report_reel')], [InlineKeyboardButton("Post", callback_data='report_post')]]
                await query.edit_message_text("Select content type:", reply_markup=InlineKeyboardMarkup(keyboard))
            
            elif callback.startswith('report_'):
                content_type = callback.replace('report_', '')
                context.user_data['content_type'] = content_type
                if content_type == 'profile':
                    await self.show_categories(update, context)
                else:
                    keyboard = [[InlineKeyboardButton("All", callback_data=f'report_all_{content_type}')], [InlineKeyboardButton("Single", callback_data=f'report_single_{content_type}')]]
                    await query.edit_message_text("Report mode:", reply_markup=InlineKeyboardMarkup(keyboard))
            
            elif callback.startswith('report_all_'):
                content_type = callback.replace('report_all_', '')
                context.user_data['content_type'] = content_type
                context.user_data['report_mode'] = 'all'
                await self.show_categories(update, context)
            
            elif callback.startswith('report_single_'):
                content_type = callback.replace('report_single_', '')
                context.user_data['content_type'] = content_type
                context.user_data['report_mode'] = 'single'
                context.user_data['state'] = 'input_item_id'
                await query.edit_message_text(f"Send {content_type} ID or link:")
            
            elif callback == 'show_categories':
                await self.show_categories(update, context)
            
            elif callback.startswith('category_'):
                category = callback.replace('category_', '')
                
                if category == 'impersonation_targets':
                    buttons = []
                    for brand in list(IMPERSONATION_TARGETS.keys()):
                        buttons.append([InlineKeyboardButton(f"impersonation {brand}", callback_data=f'imperson_brand_{brand}')])
                    buttons.append([InlineKeyboardButton("BACK", callback_data='show_categories')])
                    await query.edit_message_text("Impersonation Targets:", reply_markup=InlineKeyboardMarkup(buttons))
                
                elif category.startswith('brand_'):
                    brand = category.replace('brand_', '')
                    buttons = []
                    if brand in IMPERSONATION_TARGETS:
                        for target in IMPERSONATION_TARGETS[brand]:
                            buttons.append([InlineKeyboardButton(f"impersonation {target}", callback_data=f'reason_imperson_{brand}_{target}')])
                    buttons.append([InlineKeyboardButton("BACK", callback_data='category_impersonation_targets')])
                    await query.edit_message_text(f"impersonation {brand.upper()}:", reply_markup=InlineKeyboardMarkup(buttons))
                
                elif category in REPORT_CATEGORIES_FULL:
                    buttons = []
                    items = list(REPORT_CATEGORIES_FULL[category].items())
                    for i in range(0, len(items), 2):
                        row = []
                        for type_key, type_name in items[i:i+2]:
                            row.append(InlineKeyboardButton(f"{type_key}-{type_name[:15]}", callback_data=f'reason_{type_key}'))
                        buttons.append(row)
                    buttons.append([InlineKeyboardButton("BACK", callback_data='show_categories')])
                    await query.edit_message_text(f"Category: {category.upper()}", reply_markup=InlineKeyboardMarkup(buttons))
            
            elif callback.startswith('imperson_brand_'):
                brand = callback.replace('imperson_brand_', '')
                buttons = []
                if brand in IMPERSONATION_TARGETS:
                    for target in IMPERSONATION_TARGETS[brand]:
                        buttons.append([InlineKeyboardButton(f"impersonation {target}", callback_data=f'reason_imperson_{brand}_{target}')])
                buttons.append([InlineKeyboardButton("BACK", callback_data='category_impersonation_targets')])
                await query.edit_message_text(f"impersonation {brand.upper()}:", reply_markup=InlineKeyboardMarkup(buttons))
            
            elif callback.startswith('reason_imperson_'):
                parts = callback.replace('reason_imperson_', '').split('_', 1)
                context.user_data['reason'] = '8'
                context.user_data['imperson_target'] = parts[1] if len(parts) > 1 else 'general'
                await self.execute_reporting(update, context)
            
            elif callback.startswith('reason_'):
                reason = callback.replace('reason_', '')
                context.user_data['reason'] = reason
                context.user_data['imperson_target'] = None
                await self.execute_reporting(update, context)
            
            elif callback == 'stop_reporting':
                self.stop_flag[user_id] = True
                await query.edit_message_text("Stopping reports... Please wait")
        
        except Exception as e:
            logger.error(f"Button callback error: {e}")
    
    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        buttons = [
            [InlineKeyboardButton("Violence", callback_data='category_violence'), InlineKeyboardButton("Sexual", callback_data='category_sexual')],
            [InlineKeyboardButton("Impersonation", callback_data='category_impersonation_targets'), InlineKeyboardButton("Harassment", callback_data='category_harassment')],
            [InlineKeyboardButton("Abuse", callback_data='category_abuse'), InlineKeyboardButton("Misinformation", callback_data='category_misinformation')],
            [InlineKeyboardButton("Spam", callback_data='category_spam'), InlineKeyboardButton("Intellectual", callback_data='category_intellectual')],
            [InlineKeyboardButton("Drugs", callback_data='category_drugs'), InlineKeyboardButton("Illegal", callback_data='category_illegal')],
        ]
        await update.callback_query.edit_message_text("Select Report Category:", reply_markup=InlineKeyboardMarkup(buttons))
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            message = update.message.text.strip()
            state = context.user_data.get('state', 'idle')
            
            if state == 'waiting_code':
                if db.verify_and_use_code(message, user_id):
                    await update.message.reply_text("Access granted! Welcome to the system.")
                    db.add_user(user_id, update.effective_user.username or '', update.effective_user.first_name or '', 'user')
                    await self.show_user_menu(update, context)
                else:
                    await update.message.reply_text("Invalid access code. Try again.")
            
            elif state == 'owner_add_admin_id':
                try:
                    admin_id = int(message)
                    if admin_id == OWNER_ID:
                        await update.message.reply_text("Cannot modify owner role.")
                        return
                    db.set_user_role(admin_id, 'admin')
                    db.add_user(admin_id, '', '', 'admin', OWNER_ID)
                    await update.message.reply_text(f"User {admin_id} is now Admin")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid user ID")
            
            elif state == 'owner_remove_admin_id':
                try:
                    admin_id = int(message)
                    if admin_id == OWNER_ID:
                        await update.message.reply_text("Cannot remove owner.")
                        return
                    db.set_user_role(admin_id, 'user')
                    await update.message.reply_text(f"User {admin_id} is no longer Admin")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid user ID")
            
            elif state == 'owner_broadcast_msg':
                users = db.get_all_users()
                count = 0
                for user in users:
                    try:
                        await context.bot.send_message(user['user_id'], f"BROADCAST MESSAGE:\n\n{message}\n\n--- Developer: @{DEVELOPER_USERNAME}")
                        count += 1
                    except:
                        pass
                await update.message.reply_text(f"Broadcast sent to {count} users")
                context.user_data['state'] = 'idle'
            
            elif state == 'dash_add_sub_id':
                try:
                    target_id = int(message)
                    context.user_data['sub_user_id'] = target_id
                    context.user_data['state'] = 'dash_add_sub_days'
                    await update.message.reply_text("Enter subscription days:")
                except:
                    await update.message.reply_text("Invalid user ID")
            
            elif state == 'dash_add_sub_days':
                try:
                    days = int(message)
                    target_id = context.user_data.get('sub_user_id')
                    db.set_user_subscription(target_id, days)
                    await update.message.reply_text(f"User {target_id} subscription extended to {days} days")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid days format")
            
            elif state == 'dash_remove_user_id':
                try:
                    target_id = int(message)
                    db.set_user_role(target_id, 'expired')
                    await update.message.reply_text(f"User {target_id} removed")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid user ID")
            
            elif state == 'dash_send_to_user_id':
                if message.upper() == 'ALL':
                    context.user_data['send_to_all'] = True
                    context.user_data['state'] = 'dash_send_message'
                    await update.message.reply_text("Enter message to send:")
                else:
                    try:
                        target_id = int(message)
                        context.user_data['send_to_user'] = target_id
                        context.user_data['state'] = 'dash_send_message'
                        await update.message.reply_text("Enter message to send:")
                    except:
                        await update.message.reply_text("Invalid user ID")
            
            elif state == 'dash_send_message':
                if context.user_data.get('send_to_all'):
                    users = db.get_all_users()
                    count = 0
                    for user in users:
                        try:
                            await context.bot.send_message(user['user_id'], f"ADMIN MESSAGE:\n\n{message}")
                            count += 1
                        except:
                            pass
                    await update.message.reply_text(f"Message sent to {count} users")
                else:
                    target_id = context.user_data.get('send_to_user')
                    try:
                        await context.bot.send_message(target_id, f"ADMIN MESSAGE:\n\n{message}")
                        await update.message.reply_text(f"Message sent to {target_id}")
                    except:
                        await update.message.reply_text("Failed to send message")
                context.user_data['state'] = 'idle'
            
            elif state == 'admin_add_user_id':
                try:
                    target_id = int(message.replace('@', ''))
                    db.add_user(target_id, '', '', 'user', user_id, 30)
                    await update.message.reply_text(f"User {target_id} added with 30 days subscription")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid user ID")
            
            elif state == 'admin_create_code_input':
                if ',' not in message:
                    await update.message.reply_text("Invalid format. Use: CODE,DAYS")
                    return
                parts = message.split(',')
                code = parts[0].strip().upper()
                try:
                    days = int(parts[1].strip())
                    db.add_access_code(code, days, user_id)
                    await update.message.reply_text(f"Code created: {code} (expires in {days} days)")
                    context.user_data['state'] = 'idle'
                except:
                    await update.message.reply_text("Invalid days format")
            
            elif state == 'admin_send_msg_id':
                try:
                    target_id = int(message)
                    context.user_data['admin_msg_user'] = target_id
                    context.user_data['state'] = 'admin_send_msg_text'
                    await update.message.reply_text("Enter message:")
                except:
                    await update.message.reply_text("Invalid user ID")
            
            elif state == 'admin_send_msg_text':
                target_id = context.user_data.get('admin_msg_user')
                try:
                    await context.bot.send_message(target_id, f"ADMIN MESSAGE:\n\n{message}")
                    await update.message.reply_text(f"Message sent to {target_id}")
                except:
                    await update.message.reply_text("Failed to send message")
                context.user_data['state'] = 'idle'
            
            elif state == 'input_single_session':
                session_id = message.strip()
                if len(session_id) > 20:
                    if InstagramAPI.validate_session(session_id):
                        db.add_session(user_id, session_id)
                        await update.message.reply_text("Session added successfully")
                    else:
                        await update.message.reply_text("Session validation failed")
                else:
                    await update.message.reply_text("Invalid session format")
                context.user_data['state'] = 'idle'
            
            elif state == 'input_multi_session':
                sessions = message.split('\n')
                valid = 0
                for s in sessions:
                    s = s.strip()
                    if len(s) > 20:
                        if InstagramAPI.validate_session(s):
                            db.add_session(user_id, s)
                            valid += 1
                await update.message.reply_text(f"Sessions added: {valid}")
                context.user_data['state'] = 'idle'
            
            elif state == 'input_single_target':
                target = message.lower().replace('@', '').strip()
                target_id = InstagramAPI.get_user_id(target)
                if target_id:
                    db.add_target(user_id, target, target_id)
                    await update.message.reply_text(f"Target added: @{target}")
                else:
                    await update.message.reply_text("Target not found")
                context.user_data['state'] = 'idle'
            
            elif state == 'input_multi_target':
                targets = message.replace('\n', ' ').split()
                valid = 0
                for target in targets:
                    target = target.lower().replace('@', '').strip()
                    if target:
                        target_id = InstagramAPI.get_user_id(target)
                        if target_id:
                            db.add_target(user_id, target, target_id)
                            valid += 1
                await update.message.reply_text(f"Targets added: {valid}")
                context.user_data['state'] = 'idle'
            
            elif state == 'input_item_id':
                context.user_data['item_id'] = message.strip().split('/')[-1]
                await self.show_categories(update, context)
        
        except Exception as e:
            logger.error(f"Message handler error: {e}")
    
    async def execute_reporting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        sessions = db.get_sessions(user_id)
        targets = db.get_targets(user_id)
        reason = context.user_data.get('reason', '1')
        content_type = context.user_data.get('content_type', 'profile')
        
        if not sessions or not targets:
            await update.callback_query.edit_message_text("Error: Add sessions and targets first")
            return
        
        self.stop_flag[user_id] = False
        status_msg = await context.bot.send_message(user_id, f"Reporting started...\n\nContent Type: {content_type.upper()}\nReason: {reason}\nTargets: {len(targets)}\nSessions: {len(sessions)}\n\nStatus: Processing...\n\n[Press menu for STOP button]")
        
        keyboard = [[InlineKeyboardButton("STOP REPORTING", callback_data='stop_reporting')]]
        await context.bot.edit_message_reply_markup(chat_id=user_id, message_id=status_msg.message_id, reply_markup=InlineKeyboardMarkup(keyboard))
        
        threading.Thread(target=self.reporting_worker_infinite, args=(user_id, sessions, targets, reason, content_type, status_msg.message_id, context.bot), daemon=True).start()
    
    def reporting_worker_infinite(self, user_id: int, sessions: List[Dict], targets: List[Dict], reason: str, content_type: str, status_msg_id: int, bot):
        try:
            done = 0
            failed = 0
            update_counter = 0
            
            while not self.stop_flag.get(user_id, False):
                for target in targets:
                    if self.stop_flag.get(user_id, False):
                        break
                    
                    for session in sessions:
                        if self.stop_flag.get(user_id, False):
                            break
                        
                        success, status, msg = InstagramAPI.send_report(target['target_id'], session['session_id'], reason, content_type)
                        
                        if success:
                            done += 1
                        else:
                            failed += 1
                            if status == 429:
                                asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"ALERT: Account Banned\n\nDone: {done}\nFailed: {failed}\nSession flagged for ban detection"))
                                self.stop_flag[user_id] = True
                                return
                        
                        update_counter += 1
                        if update_counter % 5 == 0:
                            try:
                                asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"Done: {done} | Failed: {failed} | Target: @{target['target_username']}\n\nContinuing..."))
                            except:
                                pass
            
            asyncio.run(bot.edit_message_text(chat_id=user_id, message_id=status_msg_id, text=f"Reporting Stopped\n\nTotal Done: {done}\nTotal Failed: {failed}\nDeveloper: @{DEVELOPER_USERNAME}"))
            self.stop_flag.pop(user_id, None)
        except:
            pass
    
    def run(self):
        logger.info("Bot starting...")
        self.app.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
