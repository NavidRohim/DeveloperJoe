# Welcome / Objective

This is an indepth document on the DeveloperJoe Engine-- on what it does mainly. This is a bot that is fully configurable and modify-able since this project is FULLY open source including the voice libraries which are not mine. They are developed and belong to their very talanted respective developers, I say this with admiration.

- [The FFMPEG project, all contributors and dependencies](https://ffmpeg.org/about.html)
- [libopus and xiph.org](https://opus-codec.org)

This documents and all that reside alongside it serve to educate the end-user. (The person who hosts this bot)
I will walk through each command; talk about what it does, the parameters and other aspects of it.

Feel free to use this as a manual for discord users as it holds no commands or data that is sensitive to the operating of this bot.

## Warnings

This bot is not meant to be used on a large scale. it is to be used by small communities. There are costs associated with running this bot due to services that will have to be used (Like OpenAIs GPT AI Engine) which can get costly if used on a large scale. Smaller database systems are used to keep CPU usage down.

## Extra Warning

Using this bots voice capabilities will use a lot of data and a lot of resources. Please make sure your host computer can handle the demands.

### Basic Commands

The most important commands first

1. #### /help

   - This command lists all commands registered to the bot,
   - This command has no arguments.

### Chat Commands

Commands that relate to starting a chat, or anything relating to it

1. #### /start `chat_name` `stream_conversation` `ai_model` `in_thread` `speak_reply` `in_private`

   - This command starts a chat with the specifed AI model.
   - This command has 6 arguments. All are optional and defaults will be used.

        - `chat_name`: The name of the chat being created.
        - `stream_conversation`: Weather the chat will be streamed. (Text will appear gradually, like ChatGPT)
        - `ai_model`: What model of AI you want to use.
        - `in_thread`: If a special thread will be made for this chat.
        - `speak_reply`: If the chat will be spoken in a voice channel. The bot will join if this is option is enabled, and the chat owner is in a voice channel.
        - `in_private`: If the chat is private. Meaning that the chat history cannot be exported by other people with the History ID.

2. #### /ask `query` `name` `stream`

   - This command asks a question to the AI.
   - This command has 3 arguments. `name` and `stream` are optional.
      - `query`: What you want to ask DeveloperJoe.
      - `name`: Name of the chat you want to ask a question to. Like having multiple conversations in ChatGPT.
      - `stream` Weather the question posed will be streamed. This overrides the option specified when the chat was started.

3. #### /image `prompt` `save_to`

   - This command generates an image. The results may differ greatly depending on what AI model your chat is using.
   - This command has 2 arguments. `save_to` is optional.
      - `prompt`: Described version of the image you want made.
      - `save_to`: The chat where the image will be saved. This is optional, and the default chat you have saved will be used instead.

4. #### /analyse `query` `image_url` `chat_name`

   - Context
      Some terminology is used here. When I say "internal context", "analyse list" or "list" I am refering to the list of images the bot can see.
   - This command is used to ask about an image. Maybe about what is in it, the weather in the image, etc..
   - This command has 3 arguments. All are technically optional depending on situation.
      - `query`: What you want to ask about a certain image, keep in mind if you have multiple images in the list you may have to describe the image you are refering too. This argument must be left blank if you purely want to add an image to the analyse list and the analyse list cannot be empty if using this command.
      - `image_url`: The URL of the image you want to add to the analyse list. You can also add text with the `query` parameter to ask about the given image but is optional.
      - `chat_name`: The name of the chat to interact with.

5. #### /stop `name` `save_chat`

   - This command stops a chat that was started with `/start`.
   - This command has 2 arguments. `save_chat` is optional.
      - `name`: Name of the chat you want to end.
      - `save_chat`: If you want the chat to be stored for long term storage. This is active by default.

6. #### /end-all

   - This command ends all conversations a user may hold. Confirmation will be asked for.
   - This command has no arguments.

7. #### /inquire `query` `ai_model`

   - This command asks a an AI. Unlike `/ask`, context is not saved.
   - This command has 2 arguments. `ai_model` is optional.
      - `query`: What you want to ask DeveloperJoe.
      - `ai_model`: What model of AI you want to use. This is optional and a default will be used if not provided.

### Chat Settings & Management (Chat Commands)

Commands that relate configuration of management of an already existing chat.

1. #### /info `name`

   - This command retrieves in-depth information on a chat you have started. Once the chat has ended, you may no longer view the info on it.
   - This command has 1 argument. All are optional.
      - `name`: Name of the chat you want to retrieve info from. This is optional and the users default chat will be used if not provided.

2. #### /switch `chat`

   - This command switches the default chat for the user who sends the command.
   - This command has 1 argument.
      - `chat`: The chat you want to switch to.

3. #### /list

   - This command lists all chats that a user holds.
   - This command has no arguments.

4. #### /clear

   - This command clears a chats context. So anything discussed previously will be forgotten. This also clears the analyse list.
   - This command has 1 argument. It is optional.

### Voice

Commands that relate to managing voice. Some commands require you had, or still have a conversation with `speak_reply` active. (Set to `True`)

1. #### /leave

   - Leaves the voice channel the bot is currently in.
   - This command has no arguments.

2. #### /speed `speed`

   - This command changes how fast the bot can speak if enabled. I would personally not recommend anything higher 1.4
   - This command has 1 argument. (speed: decimal or round value. Anything between 1.0 and 4.0)

3. #### /volume `volume`

   - Sets bots voice volume.
   - This command has 1 argument. (volume: decimal or round value. Recommend anything between 0.0 and 1.0)

### Media (Voice)

Commands that relate to voice capabilities. All these commands require you have a conversation with `speak_reply` active. (Set to `True`)

1. #### /skip

   - This command will stop DeveloperJoe from talking if what it is saying takes to long, or you recieve a response that is not favourable.
   - This command has no arguments.
  
2. #### /pause

   - This command will pause DeveloperJoe from speaking. You can undo this with `/resume`
   - This command has no arguments.

3. #### /resume

   - This command will resume DeveloperJoe from a paused state invoked with `/pause`
   - This command has no arguments.

### History Exporting & Archiving

Commands that relate to chat history management (Like saving the transcript for later)

1. #### /export `name`

   - This command will export the transcript ONLY of a chat that is still currently active.
   - This command has 1 argument. `name` is optional.
      - `name`: The name of the chat that will be exported. If this argument is not provided, it will use the users current default chat.

2. #### /history `history_id`

   - This command will retrieve data from a chat that ended in the past and saved with `/stop`
   - This command has 1 argument.
      - `history_id`: The history ID of the chat that has been completed with `/stop` and saved for long-term storage with the `save_chat` argument active

3. #### /delete `history_id`

   - This command will delete an archived chat that was saved with `/stop`'s `save_chat` parameter.
   - This command has 1 argument.
      - `history_id`: The history ID of the chat that will be deleted.

### General

General commands that have little to no relation to a specific group.

1. #### /models

   - This command lists all models avalible to use.
   - This command has no arguments.

2. #### /times

   - This command lists all timezones avalible to use by the bot. Only used for administrative purposes but usable by all.
   - This command has no arguments.

3. #### /server

   - This command lists information about the server, it's configuration, etc..
   - This command has no arguments.

### Administrative

These commands may only be executed by the bots owner. Designated by the discord API keys account that was used.

1. #### /shutdown

   - This command shuts down the bot in a clean and effective way.
   - This command has no arguments.
   - This command can only be used by the bots owner.

2. #### /reset

   - This command resets the discord server's configuration setup. I only recommend this if the default changes or you mess something up. You will need to provide confirmation of the reset after the command is sent.
   - This command has no arguments.
   - This command can only be used by the servers administrators.

### Configuration Commands (Administrative)

These commands are used to change the configuration values viewed with `/config`

1. #### /admin voice-enabled `enable_voice`

   - This command disabled voice usage within the server the command was sent in.
   - This command has 1 argument. (enable_voice: True or False value)
   - This command can only be used by the servers administrators.

2. #### /admin set-timezone `timezone`

   - This command changes the timezone that is used at the footer of some commands (Bottom of the command)
   - This command has 1 argument. (timezone: This value has to be a valid timezone. You can view them with `/times`)
   - This command can only be used by the servers administrators.

3. #### /admin default-model `ai_model`

   - This command either changes or displays what the current server-wide default AI model is depending on what the single argument is. (Used for `/inquire`, starting chats, etc..)
   - This command has 1 argument. It is optional.

4. #### /config

   - This command lists the discord server's configuration setup (If voice is enabled, the speaking multiplier, etc...) You do NOT change the configuration here. You do it with other commands.
   - This command has no arguments.

### Model Restriction (Administrative)

*This group of commands limit what AI Models can be used by certain rank of user.
For example, if you want to lock GPT-4 behind a VIP role, you do it with:
`/lock ai_model: GPT 4 role: @VIP`*

1. #### /locks

   - This command will view all locks placed upon models.
   - This command has no arguments.

2. #### /lock `ai_model` `role`

   - This command will lock an AI Model behind a role. Higher ranked users than the specified role will still be able to use specified model since they outrank the role that was used for the lock.
   - This command has 2 arguments.
      - `ai_model`: The GPT Model you want to lock.
      - `role` The role you want it to be locked behind.

3. #### /unlock `ai_model` `role`

   - This command removes the role restriction that was placed upon by `/lock`
   - This command has 2 arguments.
      - `ai_model` The GPT Model you want to unlock.
      - `role` Role to remove the usage restriction from.

## Thread Commands

These commands can only be used inside **private** threads.

Do `@DeveloperJoe image <image prompt>` to generate an image.
Do `@DeveloperJoe analyse <query about image>` and provide some photo attachments in discord.
Or just do `@DeveloperJoe <query>` to ask a one-off question.
