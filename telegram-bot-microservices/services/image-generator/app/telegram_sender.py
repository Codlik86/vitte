"""
Telegram sender for generated images
"""
import aiohttp
from io import BytesIO

from app.config import config
from shared.utils import get_logger

logger = get_logger(__name__)


async def send_photo_to_telegram(chat_id: int, image_data: bytes) -> bool:
    """
    Send photo to Telegram chat using Bot API.

    Args:
        chat_id: Telegram chat ID
        image_data: Image bytes

    Returns:
        True if sent successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto"

    # Prepare multipart form data
    form_data = aiohttp.FormData()
    form_data.add_field('chat_id', str(chat_id))
    form_data.add_field(
        'photo',
        BytesIO(image_data),
        filename='generated.png',
        content_type='image/png'
    )

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=form_data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        logger.info(f"Photo sent successfully to chat {chat_id}")
                        return True
                    else:
                        logger.error(f"Telegram API error: {result}")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send photo: {response.status} - {error_text}")
                    return False

    except Exception as e:
        logger.error(f"Error sending photo to Telegram: {e}")
        return False
