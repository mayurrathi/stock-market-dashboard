"""
Telegram Monitor - Monitors Telegram channels for stock market data/signals
"""
import asyncio
import re
from telethon import TelegramClient, events, errors
from telethon.errors import FloodWaitError
from .database import SessionLocal
from .models import TelegramMessage, Log, Config, FetchLog, Recommendation
from .analyzer import analyzer
import logging
import pytz

IST = pytz.timezone('Asia/Kolkata')

logger = logging.getLogger(__name__)

# Regex to find URLs in text
URL_REGEX = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


class TelegramMonitor:
    def __init__(self):
        self.client = None
        self.is_running = False
        self.monitored_chats = []
        self._api_id = None
        self._api_hash = None

    async def initialize(self, api_id, api_hash, session_name=None):
        """Initialize the Telegram client with API credentials"""
        # Store credentials for reconnection
        self._api_id = api_id
        self._api_hash = api_hash
        
        # Use data directory for session persistence
        import os
        if session_name is None:
            session_name = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "data", 
                "stock_monitor"
            )
        
        if self.client:
            # Disconnect existing client first
            try:
                await self.client.disconnect()
            except:
                pass
            self.client = None
        
        self.client = TelegramClient(session_name, api_id, api_hash)
        try:
            await self.client.connect()
        except FloodWaitError as e:
            logger.warning(f"Telegram FloodWait triggered during init. Waiting {e.seconds}s required. Skipping connection.")
            # We don't wait here to avoid blocking server startup
            self.client = None
        except Exception as e:
            logger.error(f"Failed to connect Telegram client: {e}")
            self.client = None


    async def _ensure_connected(self):
        """Ensure the client is connected, reconnect if needed"""
        if not self.client:
            raise Exception("Client not initialized")
        
        if not self.client.is_connected():
            logger.info("Telegram client disconnected, reconnecting...")
            await self.client.connect()
            logger.info("Telegram client reconnected")

    async def send_code(self, phone):
        """Send verification code to phone number"""
        if not self.client:
            raise Exception("Client not initialized")
        await self._ensure_connected()
        
        # Store the phone code hash for verification
        result = await self.client.send_code_request(phone)
        self._phone_code_hash = result.phone_code_hash
        self._pending_phone = phone
        
        return {"status": "code_sent"}

    async def verify_code(self, phone, code, two_fa_password=None):
        """Verify the authentication code"""
        if not self.client:
            raise Exception("Client not initialized")
        await self._ensure_connected()
        
        await asyncio.sleep(0.5)
        
        try:
            phone_code_hash = getattr(self, '_phone_code_hash', None)
            
            if phone_code_hash and getattr(self, '_pending_phone', None) == phone:
                await self.client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            else:
                await self.client.sign_in(phone, code, password=two_fa_password)
            
            # Clear stored hash after successful auth
            self._phone_code_hash = None
            self._pending_phone = None
            
            return {"status": "authenticated"}
        except Exception as e:
            error_msg = str(e).lower()
            if "two-step" in error_msg or "password" in error_msg:
                return {"status": "2fa_required", "message": "Two-factor authentication required"}
            return {"status": "error", "message": str(e)}

    async def start_monitoring(self, chat_ids_or_usernames: list):
        """Start monitoring specified Telegram channels for new messages"""
        if not self.client:
            logger.warning("Telegram client not initialized. Cannot start monitoring.")
            return

        if not await self.client.is_user_authorized():
            raise Exception("Client not authorized")

        self.monitored_chats = chat_ids_or_usernames
        self.is_running = True

        @self.client.on(events.NewMessage(chats=chat_ids_or_usernames))
        async def handler(event):
            # Check if system monitoring is enabled
            db = SessionLocal()
            try:
                sys_mon = db.query(Config).filter(Config.key == "system_monitoring_enabled").first()
                if sys_mon and sys_mon.value == "false":
                    return # Skip processing if disabled
            finally:
                db.close()
                
            await self.process_message(event)

        logger.info(f"Telegram monitoring started for {len(chat_ids_or_usernames)} channels...")

    async def process_message(self, event):
        """Process incoming Telegram messages with AI analysis"""
        from .llm import llm_service
        from .stock_api import stock_api
        from .recommendation_engine import recommendation_engine
        from .technical_analysis import technical_analyzer
        
        text = event.message.text
        if not text:
            return
        
        # Get channel info
        channel_id = str(event.chat_id)
        channel_name = event.chat.title if hasattr(event.chat, 'title') else str(event.chat_id)
        message_id = event.message.id

        # Extract URLs from message
        urls = URL_REGEX.findall(text)
        
        db = SessionLocal()
        try:
            # Check for duplicate message
            existing = db.query(TelegramMessage).filter(
                TelegramMessage.message_id == message_id,
                TelegramMessage.channel_id == channel_id
            ).first()
            
            if existing:
                logger.debug(f"Duplicate message {message_id} from {channel_name}")
                return
            
            # Extract stocks using AI if available, else fallback to regex
            if llm_service.is_available():
                stocks = await llm_service.extract_stocks_from_message(text)
                logger.info(f"AI extracted stocks: {stocks}")
            else:
                stocks = analyzer.extract_stocks(text)
                logger.info(f"Regex extracted stocks: {stocks}")
            
            # Store the message
            new_message = TelegramMessage(
                message_id=message_id,
                channel_id=channel_id,
                channel_name=channel_name,
                text=text,
                urls=urls if urls else None,
                extracted_stocks=stocks if stocks else None,
                processed=False,
                message_date=event.message.date.astimezone(IST)
            )
            db.add(new_message)
            
            # Log the capture
            new_log = Log(level="INFO", message=f"Captured message from {channel_name}: {text[:50]}...")
            db.add(new_log)
            
            db.commit()
            logger.info(f"Stored message from {channel_name}")
            
            # Deep Research + AI Recommendation for each stock
            if stocks:
                logger.info(f"Starting deep research for stocks: {stocks}")
                for stock in stocks:
                    try:
                        # Step 1: Get fundamentals
                        fundamentals = stock_api.get_fundamentals(stock)
                        
                        # Step 2: Get technical analysis
                        history = await stock_api.get_stock_history(stock)
                        technical_data = technical_analyzer.analyze(history)
                        
                        # Step 3: Get existing engine recommendation
                        sentiment, confidence = analyzer.analyze_sentiment(text)
                        existing_rec = {
                            "action": "BUY" if sentiment == "bullish" else "SELL" if sentiment == "bearish" else "HOLD",
                            "confidence": confidence * 100
                        }
                        
                        # Step 4: Try AI synthesis if available
                        if llm_service.is_available():
                            ai_rec = await llm_service.synthesize_recommendation(
                                symbol=stock,
                                message_text=text,
                                fundamentals=fundamentals or {},
                                recommendation_data=existing_rec,
                                technical_analysis=technical_data, # Pass technical data
                                news_context=""
                            )
                            if ai_rec:
                                rec = Recommendation(
                                    symbol=stock,
                                    timeframe="next_day",
                                    action=ai_rec.get("action", "HOLD"),
                                    confidence=ai_rec.get("confidence", 50),
                                    reasoning=ai_rec.get("summary", f"AI analysis from {channel_name}")
                                )
                                db.add(rec)
                                logger.info(f"AI recommendation for {stock}: {ai_rec.get('action')}")
                                continue
                        
                        # Fallback: Use existing logic
                        rec = Recommendation(
                            symbol=stock,
                            timeframe="next_day",
                            action=existing_rec["action"],
                            confidence=existing_rec["confidence"],
                            reasoning=f"Real-time analysis from {channel_name}: {text[:150]}..."
                        )
                        db.add(rec)
                        
                    except Exception as e:
                        logger.error(f"Error processing stock {stock}: {e}")
                        continue
                
                db.commit()
                logger.info(f"Generated recommendations for {len(stocks)} stocks")
            
        except Exception as e:
            logger.error(f"Error processing/analyzing message: {e}")
            db.rollback()
        finally:
            db.close()

    async def fetch_channel_history(self, channel_username: str, limit: int = 50) -> int:
        """Fetch recent messages from a Telegram channel on-demand.
        Returns the number of messages added.
        """
        # Auto-reconnect if client is not initialized or not connected
        if not self.client or not self.client.is_connected():
            db = SessionLocal()
            try:
                api_id = db.query(Config).filter(Config.key == "telegram_api_id").first()
                api_hash = db.query(Config).filter(Config.key == "telegram_api_hash").first()
                
                if api_id and api_hash:
                    logger.info("Auto-reconnecting Telegram client...")
                    await self.initialize(int(api_id.value), api_hash.value)
                else:
                    logger.warning("No Telegram credentials found in database")
                    return 0
            except Exception as e:
                logger.error(f"Failed to auto-reconnect Telegram: {e}")
                return 0
            finally:
                db.close()
        
        if not self.client or not await self.client.is_user_authorized():
            logger.warning("Telegram client not authorized, cannot fetch channel history")
            return 0
        
        await self._ensure_connected()
        
        messages_added = 0
        db = SessionLocal()
        
        try:
            # Get the channel entity - handle numeric IDs
            try:
                # Try to parse as integer (for channel IDs like -1001234567890)
                entity_input = channel_username
                if channel_username.lstrip('-').isdigit():
                    entity_input = int(channel_username)
                
                channel = await self.client.get_entity(entity_input)
                channel_name = channel.title if hasattr(channel, 'title') else channel_username
                channel_id = str(channel.id) if hasattr(channel, 'id') else channel_username
            except Exception as e:
                logger.error(f"Failed to get channel entity for {channel_username}: {e}")
                db.close()
                return 0
            
            # Fetch recent messages
            async for message in self.client.iter_messages(channel, limit=limit):
                if not message.text:
                    continue
                
                text = message.text
                message_id = message.id
                urls = URL_REGEX.findall(text)
                
                # Check for duplicate
                existing = db.query(TelegramMessage).filter(
                    TelegramMessage.message_id == message_id,
                    TelegramMessage.channel_id == channel_id
                ).first()
                
                if existing:
                    continue
                
                # Store the message
                new_message = TelegramMessage(
                    message_id=message_id,
                    channel_id=channel_id,
                    channel_name=channel_name,
                    text=text,
                    urls=urls if urls else None,
                    processed=False,
                    message_date=message.date.astimezone(IST)
                )
                db.add(new_message)
                messages_added += 1
            
            # Log the fetch operation
            fetch_log = FetchLog(
                source_name=channel_name,
                items_fetched=messages_added,
                status="success"
            )
            db.add(fetch_log)
            
            db.commit()
            logger.info(f"Fetched {messages_added} messages from Telegram channel: {channel_name}")
            
        except Exception as e:
            logger.error(f"Error fetching channel history: {e}")
            db.rollback()
            
            # Log the error
            fetch_log = FetchLog(
                source_name=channel_username,
                items_fetched=0,
                status="error",
                error_message=str(e)
            )
            db.add(fetch_log)
            db.commit()
        finally:
            db.close()
        
        return messages_added

    async def is_authorized(self) -> bool:
        """Check if the Telegram client is authorized"""
        if not self.client:
            return False
        try:
            await self._ensure_connected()
            return await self.client.is_user_authorized()
        except:
            return False

    def get_status(self) -> dict:
        """Get the current status of the Telegram monitor"""
        return {
            "is_running": self.is_running,
            "monitored_channels": len(self.monitored_chats),
            "client_initialized": self.client is not None
        }


# Global monitor instance
monitor = TelegramMonitor()
