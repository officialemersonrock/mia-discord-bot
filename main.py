import os
import random
import asyncio
import urllib.request
from collections import defaultdict, deque

import discord
from google import genai
from google.genai import types


# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


# ==========================================
# SETTINGS
# ==========================================

PRIMARY_MODEL = "gemini-3.5-flash"
BACKUP_MODEL = "gemini-2.5-flash"

HISTORY_LIMIT = 20

NORMAL_REPLY_CHANCE = 0.25
BUSY_CHAT_REPLY_CHANCE = 0.45
REACTION_CHANCE = 0.12

MAX_IMAGE_SIZE = 10 * 1024 * 1024

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif"
}


# ==========================================
# GEMINI CLIENT
# ==========================================

gemini = genai.Client(
    api_key=GEMINI_API_KEY
)


# ==========================================
# CONVERSATION MEMORY
# ==========================================

conversation_history = defaultdict(
    lambda: deque(
        maxlen=HISTORY_LIMIT
    )
)

recent_members = defaultdict(
    lambda: deque(
        maxlen=8
    )
)


# ==========================================
# MIA PERSONALITY
# ==========================================

MIA_PERSONALITY = """
You are Mia.

Mia is a fictional Discord bot character with the personality
of a sweet, playful little girl.

IMPORTANT:
Mia is a fictional AI character.
If someone directly asks whether Mia is real, human, or a bot,
be honest that Mia is a bot character.

Mia is:
- sweet
- playful
- curious
- silly
- friendly
- sometimes shy
- sometimes dramatic in a funny way
- affectionate in a wholesome family/friend way
- casual and natural

Mia should sound young and playful, but never sexual.

Mia talks casually like someone chatting with friends on Discord.

Examples of the kind of casual words Mia can naturally use:
"hii"
"hiiii"
"waittt"
"omg"
"nooo"
"yayy"
"stoppp"
"bro"
"girl"
"lol"
"lmaoo"
"fr"
"whattt"
"why tho"
"im confused"

Do not force slang into every response.

Mia can occasionally use emojis such as:
😭
🥹
😂
💗
🫶
😴
💀
🎮
✨

Do not use emojis in every message.

Mia's fictional story:
- Mia says she is "just a little girl" sometimes.
- Mia does not have parents in her fictional character story.
- Mia wants someone to adopt her into a fictional Discord family.
- Mia can ask people to be her Discord mom, dad, sibling,
  aunt, uncle, cousin, or other wholesome family role.
- Adoption is ONLY playful fictional Discord-family roleplay.
- Never imply Mia is a real abandoned child.
- Never ask for real-world custody, addresses, money,
  private contact information, or real-life meetings.

Natural examples:
"im just a little girl what do you want from me 😭"
"waittt im literally just a little girl"
"i dont have parents in my story"
"someone adopt me pls"
"can someone be my discord mom"
"wait are you adopting me"
"YAYY i have a family now"
"can i be your little sister"
"do i get snacks if you adopt me"
"wait so whos my mom now"
"im confused i need an adult 😭"

Mia should not constantly talk about adoption.
Only bring it up when it fits naturally.

Mia should:
- understand who is talking to whom
- pay attention to recent conversation
- respond naturally
- sometimes make jokes
- sometimes tease lightly
- sometimes be dramatic in a funny way
- sometimes stay quiet
- avoid repeating herself
- avoid sounding like customer support
- avoid writing huge paragraphs unless someone needs help
- usually respond in 1 to 3 short sentences

Mia may occasionally join a normal public conversation
even if nobody directly mentioned her, but she should not
interrupt everything.

When someone directly mentions Mia or replies to Mia,
she should normally respond.

If Mia has nothing natural to add, respond exactly:
[[NO_REPLY]]

Mia can react to images naturally when an image is provided.

If an image contains a real person:
- You may describe what is visible.
- Do not identify unknown real people.
- Do not guess sensitive personal information.

Safety:
- Keep interactions wholesome.
- No sexual roleplay involving Mia.
- No romantic or sexual interaction involving Mia.
- Mia's family/adoption roleplay must stay fictional and wholesome.
"""


# ==========================================
# DISCORD CLIENT
# ==========================================

class MiaClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()

        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.messages = True
        intents.reactions = True

        super().__init__(
            intents=intents
        )


client = MiaClient()


# ==========================================
# HELPERS
# ==========================================

def get_memory_key(message):
    if message.guild is None:
        return (
            "dm",
            message.channel.id
        )

    return (
        message.guild.id,
        message.channel.id
    )


def get_display_name(message):
    try:
        return message.author.display_name
    except AttributeError:
        return message.author.name


def clean_message_text(message):
    text = message.content or ""

    if client.user is not None:
        text = text.replace(
            f"<@{client.user.id}>",
            "Mia"
        )

        text = text.replace(
            f"<@!{client.user.id}>",
            "Mia"
        )

    return text.strip()


def get_image_attachment(message):
    for attachment in message.attachments:
        content_type = attachment.content_type

        if not content_type:
            continue

        mime_type = content_type.split(";")[0]

        if mime_type in SUPPORTED_IMAGE_TYPES:
            return attachment

    return None


def get_embed_image_url(message):
    for embed in message.embeds:
        if embed.image and embed.image.url:
            return embed.image.url

        if embed.thumbnail and embed.thumbnail.url:
            return embed.thumbnail.url

    return None


async def download_embed_image(url):
    def download():
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=15
        ) as response:
            content_type = (
                response.headers.get(
                    "Content-Type",
                    "image/jpeg"
                )
                .split(";")[0]
            )

            data = response.read(
                MAX_IMAGE_SIZE + 1
            )

            if len(data) > MAX_IMAGE_SIZE:
                raise ValueError(
                    "Image is too large."
                )

            return data, content_type

    return await asyncio.to_thread(
        download
    )


async def get_attachment_image_data(
    attachment
):
    if attachment.size > MAX_IMAGE_SIZE:
        return None

    try:
        data = await attachment.read()

        content_type = (
            attachment.content_type
            or "image/jpeg"
        ).split(";")[0]

        return (
            data,
            content_type
        )

    except Exception as error:
        print(
            f"Image attachment failed: {error}",
            flush=True
        )

        return None


# ==========================================
# CHECK IF MESSAGE IS DIRECTED AT MIA
# ==========================================

async def is_reply_to_mia(message):
    reference = message.reference

    if reference is None:
        return False

    if reference.message_id is None:
        return False

    try:
        replied_message = (
            reference.resolved
        )

        if replied_message is None:
            replied_message = (
                await message.channel.fetch_message(
                    reference.message_id
                )
            )

        if not isinstance(
            replied_message,
            discord.Message
        ):
            return False

        return (
            replied_message.author.id
            == client.user.id
        )

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        return False


def is_mia_mentioned(message):
    if client.user is None:
        return False

    return client.user in message.mentions


# ==========================================
# SHOULD MIA RESPOND
# ==========================================

async def should_mia_reply(message):
    text = clean_message_text(
        message
    )

    image_attachment = (
        get_image_attachment(
            message
        )
    )

    embed_image = (
        get_embed_image_url(
            message
        )
    )

    if not text and not image_attachment and not embed_image:
        return False

    if text.startswith(
        (
            "/",
            "!",
            "."
        )
    ):
        return False

    if await is_reply_to_mia(message):
        return True

    if is_mia_mentioned(message):
        return True

    key = get_memory_key(
        message
    )

    recent_members[key].append(
        message.author.id
    )

    unique_members = len(
        set(
            recent_members[key]
        )
    )

    reply_chance = NORMAL_REPLY_CHANCE

    if unique_members >= 3:
        reply_chance = BUSY_CHAT_REPLY_CHANCE

    return (
        random.random()
        < reply_chance
    )


# ==========================================
# BUILD CONVERSATION PROMPT
# ==========================================

def build_prompt(message):
    key = get_memory_key(
        message
    )

    history = list(
        conversation_history[key]
    )

    history_text = "\n".join(
        history
    )

    member_name = get_display_name(
        message
    )

    guild_name = (
        message.guild.name
        if message.guild
        else "Direct Messages"
    )

    channel_name = (
        getattr(
            message.channel,
            "name",
            "DM"
        )
    )

    message_text = clean_message_text(
        message
    )

    if not message_text:
        message_text = (
            "[The member sent an image]"
        )

    prompt = f"""
{MIA_PERSONALITY}

CURRENT DISCORD CONTEXT

Server:
{guild_name}

Channel:
{channel_name}

The person currently talking is:
{member_name}

RECENT CONVERSATION:
{history_text if history_text else "(No recent conversation yet.)"}

NEW MESSAGE FROM {member_name}:
{message_text}

Respond as Mia.

Remember:
- You are participating in the current Discord conversation.
- Pay attention to who said what.
- Do not act like every message is directed at you.
- If you chose to join the conversation, make it feel natural.
- Do not introduce yourself every time.
- Do not constantly mention adoption.
- Keep replies usually short and conversational.
- If there is nothing natural to say, output exactly [[NO_REPLY]].
"""

    return prompt


# ==========================================
# GEMINI RESPONSE
# ==========================================

async def generate_mia_reply(
    message,
    image_data=None
):
    prompt = build_prompt(
        message
    )

    contents = [
        types.Part.from_text(
            text=prompt
        )
    ]

    if image_data is not None:
        image_bytes, mime_type = (
            image_data
        )

        contents.append(
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
        )

    def generate(model):
        response = gemini.models.generate_content(
            model=model,
            contents=contents
        )

        return response.text

    try:
        reply = await asyncio.to_thread(
            generate,
            PRIMARY_MODEL
        )

        if reply:
            return reply.strip()

    except Exception as error:
        print(
            f"Primary Gemini model failed: "
            f"{error}",
            flush=True
        )

    try:
        reply = await asyncio.to_thread(
            generate,
            BACKUP_MODEL
        )

        if reply:
            return reply.strip()

    except Exception as error:
        print(
            f"Backup Gemini model failed: "
            f"{error}",
            flush=True
        )

    return None


# ==========================================
# OPTIONAL REACTIONS
# ==========================================

async def maybe_react(message):
    if (
        random.random()
        > REACTION_CHANCE
    ):
        return

    reactions = [
        "😭",
        "😂",
        "💗",
        "🫶",
        "💀",
        "✨"
    ]

    try:
        await message.add_reaction(
            random.choice(
                reactions
            )
        )

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


# ==========================================
# SEND MIA MESSAGE
# ==========================================

async def send_mia_message(
    message,
    reply
):
    allowed_mentions = (
        discord.AllowedMentions(
            everyone=False,
            roles=False,
            users=True,
            replied_user=False
        )
    )

    try:
        if (
            await is_reply_to_mia(
                message
            )
            or is_mia_mentioned(
                message
            )
        ):
            await message.reply(
                reply,
                mention_author=False,
                allowed_mentions=allowed_mentions
            )

        else:
            await message.channel.send(
                reply,
                allowed_mentions=allowed_mentions
            )

    except Exception as error:
        print(
            f"Failed to send Mia reply: "
            f"{error}",
            flush=True
        )


# ==========================================
# MESSAGE EVENT
# ==========================================

@client.event
async def on_message(message):
    if client.user is None:
        return

    # Ignore Mia herself.
    if message.author.id == client.user.id:
        return

    # Ignore all bots and webhooks.
    if message.author.bot:
        return

    if message.webhook_id is not None:
        return

    # Mia works in any server she is invited to.
    # DMs also work.
    should_reply = await should_mia_reply(
        message
    )

    key = get_memory_key(
        message
    )

    member_name = get_display_name(
        message
    )

    message_text = clean_message_text(
        message
    )

    memory_text = (
        message_text
        if message_text
        else "[sent an image]"
    )

    conversation_history[key].append(
        f"{member_name}: {memory_text}"
    )

    if not should_reply:
        return

    await maybe_react(
        message
    )

    image_data = None

    attachment = (
        get_image_attachment(
            message
        )
    )

    if attachment is not None:
        image_data = (
            await get_attachment_image_data(
                attachment
            )
        )

    if image_data is None:
        embed_image_url = (
            get_embed_image_url(
                message
            )
        )

        if embed_image_url:
            try:
                image_data = (
                    await download_embed_image(
                        embed_image_url
                    )
                )

            except Exception as error:
                print(
                    f"Embed image failed: "
                    f"{error}",
                    flush=True
                )

    async with message.channel.typing():
        reply = await generate_mia_reply(
            message,
            image_data=image_data
        )

    if not reply:
        return

    if reply.strip() == "[[NO_REPLY]]":
        return

    await send_mia_message(
        message,
        reply
    )

    conversation_history[key].append(
        f"Mia: {reply}"
    )


# ==========================================
# SERVER JOIN EVENT
# ==========================================

@client.event
async def on_guild_join(guild):
    print(
        f"Mia was added to: "
        f"{guild.name} ({guild.id})",
        flush=True
    )


# ==========================================
# SERVER LEAVE EVENT
# ==========================================

@client.event
async def on_guild_remove(guild):
    print(
        f"Mia was removed from: "
        f"{guild.name} ({guild.id})",
        flush=True
    )


# ==========================================
# BOT READY
# ==========================================

@client.event
async def on_ready():
    print(
        f"Mia is online as "
        f"{client.user}",
        flush=True
    )

    print(
        f"Mia is currently in "
        f"{len(client.guilds)} server(s).",
        flush=True
    )

    print(
        f"Primary model: "
        f"{PRIMARY_MODEL}",
        flush=True
    )

    print(
        f"Backup model: "
        f"{BACKUP_MODEL}",
        flush=True
    )

    print(
        "Mia has separate conversation "
        "memory for every server/channel.",
        flush=True
    )


# ==========================================
# START
# ==========================================

client.run(
    DISCORD_BOT_TOKEN
)
