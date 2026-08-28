import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "8633921744:AAFi3Dffbdcr4WBPzoJj3KhyApK4wg_iBuI"  # <-- PUT YOUR BOT TOKEN HERE

CHANNEL_USERNAME = "@eren_xo"
CHANNEL_LINK = "https://t.me/eren_xo"

REFERRAL_REWARD = 7
MIN_WITHDRAWAL = 100

# Temporary in-memory database
users = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# USER DATABASE
# ============================================================

def get_user(user_id):
    """Create/get a user's temporary account."""
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "referrals": 0,
            "referred_by": None,
            "withdrawals": [],
        }

    return users[user_id]


# ============================================================
# CHANNEL MEMBERSHIP CHECK
# ============================================================

async def is_channel_member(bot, user_id):
    """Check whether a user has joined the required channel."""
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id,
        )

        return member.status in (
            "member",
            "administrator",
            "creator",
        )

    except Exception as e:
        logger.warning(
            "Membership check failed for %s: %s",
            user_id,
            e,
        )
        return False


# ============================================================
# JOIN CHECK SCREEN
# ============================================================

def join_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Join Channel",
                url=CHANNEL_LINK,
            )
        ],
        [
            InlineKeyboardButton(
                "✅ I've Joined",
                callback_data="check_join",
            )
        ],
    ])


async def show_join_screen(update: Update):
    text = (
        "🔒 <b>Channel Verification Required</b>\n\n"
        "To use this bot, you must first join our channel.\n\n"
        "1️⃣ Tap <b>Join Channel</b>\n"
        "2️⃣ Join the channel\n"
        "3️⃣ Come back and tap <b>I've Joined</b>\n\n"
        "After verification, all bot features will be unlocked."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=join_keyboard(),
        )
    else:
        await update.message.reply_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=join_keyboard(),
        )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():
    """
    2 x 2 button layout
    """

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 Balance",
                callback_data="balance",
            ),
            InlineKeyboardButton(
                "👥 Referrals",
                callback_data="referrals",
            ),
        ],
        [
            InlineKeyboardButton(
                "💸 Withdraw",
                callback_data="withdraw",
            ),
            InlineKeyboardButton(
                "📖 How to Earn",
                callback_data="guide",
            ),
        ],
    ])


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"🎉 <b>Welcome, {user.first_name}!</b>\n\n"
        "💎 <b>Refer & Earn</b>\n\n"
        f"Earn <b>₹{REFERRAL_REWARD}</b> for every successful referral.\n\n"
        "Choose an option below:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
    else:
        await update.message.reply_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )


# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    account = get_user(user_id)

    # --------------------------------------------------------
    # REFERRAL PROCESSING
    # --------------------------------------------------------

    if context.args:
        referral_code = context.args[0]

        try:
            referrer_id = int(referral_code)

            # Don't allow self-referral
            if referrer_id != user_id:

                # Only assign referral once
                if account["referred_by"] is None:

                    referrer = get_user(referrer_id)

                    account["referred_by"] = referrer_id

                    referrer["referrals"] += 1
                    referrer["balance"] += REFERRAL_REWARD

                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=(
                                "🎉 <b>New Referral!</b>\n\n"
                                f"Someone joined using your referral link.\n\n"
                                f"💰 <b>+₹{REFERRAL_REWARD}</b>\n"
                                f"👥 Total referrals: "
                                f"<b>{referrer['referrals']}</b>"
                            ),
                            parse_mode=ParseMode.HTML,
                        )
                    except Exception:
                        pass

        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------
    # CHANNEL CHECK
    # --------------------------------------------------------

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await show_join_screen(update)
        return

    await show_main_menu(update, context)


# ============================================================
# JOIN VERIFICATION CALLBACK
# ============================================================

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await query.answer(
            "❌ You haven't joined the channel yet.",
            show_alert=True,
        )

        await query.edit_message_reply_markup(
            reply_markup=join_keyboard()
        )
        return

    await query.edit_message_text(
        "✅ <b>Verification successful!</b>\n\n"
        "You can now use all bot features.",
        parse_mode=ParseMode.HTML,
    )

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "🎉 <b>Welcome to the Refer & Earn Bot!</b>\n\n"
            "Choose an option below:"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )


# ============================================================
# BALANCE
# ============================================================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await show_join_screen(update)
        return

    account = get_user(user_id)

    text = (
        "💰 <b>Your Balance</b>\n\n"
        f"💵 Balance: <b>₹{account['balance']}</b>\n"
        f"👥 Referrals: <b>{account['referrals']}</b>\n\n"
        f"Minimum withdrawal: <b>₹{MIN_WITHDRAWAL}</b>"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


# ============================================================
# REFERRAL INFO
# ============================================================

async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await show_join_screen(update)
        return

    account = get_user(user_id)

    bot_username = context.bot.username

    referral_link = (
        f"https://t.me/{bot_username}?start={user_id}"
    )

    text = (
        "👥 <b>Referral Program</b>\n\n"
        f"💰 Reward per referral: <b>₹{REFERRAL_REWARD}</b>\n"
        f"👤 Your referrals: <b>{account['referrals']}</b>\n"
        f"💵 Your balance: <b>₹{account['balance']}</b>\n\n"
        "🔗 <b>Your Referral Link:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        "Share this link with your friends.\n"
        "When they join and start the bot, the referral "
        "will be counted."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📤 Share Link",
                url=(
                    "https://t.me/share/url?"
                    f"url={referral_link}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ],
    ])

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


# ============================================================
# WITHDRAW
# ============================================================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await show_join_screen(update)
        return

    account = get_user(user_id)

    if account["balance"] < MIN_WITHDRAWAL:
        text = (
            "💸 <b>Withdrawal</b>\n\n"
            f"Your current balance is "
            f"<b>₹{account['balance']}</b>.\n\n"
            f"❌ Minimum withdrawal is "
            f"<b>₹{MIN_WITHDRAWAL}</b>.\n\n"
            f"Invite more friends to earn "
            f"<b>₹{REFERRAL_REWARD}</b> per referral."
        )
    else:
        text = (
            "💸 <b>Withdrawal Available</b>\n\n"
            f"Your balance: <b>₹{account['balance']}</b>\n\n"
            "For this example bot, withdrawal requests are "
            "stored temporarily.\n\n"
            "Contact the bot owner/admin to process your "
            "withdrawal."
        )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


# ============================================================
# EARNING GUIDE
# ============================================================

async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await show_join_screen(update)
        return

    text = (
        "📖 <b>How to Earn</b>\n\n"
        "1️⃣ Join the required channel.\n\n"
        "2️⃣ Open your referral section.\n\n"
        "3️⃣ Copy your personal referral link.\n\n"
        "4️⃣ Share it with your friends.\n\n"
        f"5️⃣ Earn <b>₹{REFERRAL_REWARD}</b> for each "
        "successful referral.\n\n"
        f"6️⃣ Once your balance reaches "
        f"<b>₹{MIN_WITHDRAWAL}</b>, you can request a "
        "withdrawal.\n\n"
        "⚠️ Referral rewards should only be given for genuine "
        "new users. Self-referrals and fake accounts should "
        "not be rewarded."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


# ============================================================
# BACK BUTTON
# ============================================================

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await show_join_screen(update)
        return

    await show_main_menu(update, context)


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    action = query.data

    if action == "check_join":
        await check_join(update, context)

    elif action == "balance":
        await balance(update, context)

    elif action == "referrals":
        await referrals(update, context)

    elif action == "withdraw":
        await withdraw(update, context)

    elif action == "guide":
        await guide(update, context)

    elif action == "back":
        await back(update, context)

    else:
        await query.answer(
            "Unknown option.",
            show_alert=True,
        )


# ============================================================
# UNKNOWN TEXT
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    if not await is_channel_member(
        context.bot,
        user_id,
    ):
        await show_join_screen(update)
        return

    await update.message.reply_text(
        "👇 Please select an option from the menu.",
        reply_markup=main_menu(),
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Exception while handling update:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN is empty. Put your Telegram bot token "
            "inside the BOT_TOKEN variable."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    application.add_handler(
        # Any normal text message
        # that isn't /start
        __import__(
            "telegram.ext",
            fromlist=["MessageHandler", "filters"]
        ).MessageHandler(
            __import__(
                "telegram.ext",
                fromlist=["filters"]
            ).filters.TEXT
            & ~__import__(
                "telegram.ext",
                fromlist=["filters"]
            ).filters.COMMAND,
            handle_message,
        )
    )

    application.add_error_handler(error_handler)

    print("🤖 Bot is running...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()