# 🏁 Mario Kart 8 Time Attack Discord Bot

A Discord bot for organizing Time Attack tournaments for Mario Kart 8 Deluxe. Players can participate in time trial competitions on random tracks, with automatic score tracking and leaderboard management.

> **Note**: This project is currently under development.

## ✨ Features

- **Time Attack Tournaments**: Organize tournaments on random tracks
- **Score Management**: Record and verify participants' times
- **Automatic Leaderboard**: Real-time updates of best times
- **Verification System**: Support for screenshot proof submission
- **Automatic Reminders**: Notifications before tournament end
- **Automatic Completion**: Closing and announcing results at deadline

## 🛠️ Prerequisites

### Python
- 3.8 or higher

### Discord
- Discord bot account and token
- Appropriate permissions
   - Bot
      - Send Messages
      - Embed Links
      - Attach Files
      - Read Message History
      - Manage Messages
   - Scopes
      - bot
      - applications.commands

## 📋 Installation

1. **Clone the repository**
   ```
   git clone https://github.com/ncarli/mk-timetrials-discord-bot
   cd mk-timetrials-discord-bot
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Configuration**
   - Create a `.env` file based on the `.env.example` template
   - Add your Discord token to the `.env` file
   ```
   DISCORD_TOKEN=your_discord_token_here
   ```

4. **Database initialization**
   - The SQLite database will be automatically created on first start
   - Mario Kart 8 Deluxe track data is preloaded

## 🚀 Getting Started

```
python main.py
```

## 🎮 Commands

### Tournament Commands
- `/tournoi [classe] [duree] [course]` - Creates a new tournament (admin only)
- `/participer` - Registers the user for the current tournament
- `/info` - Displays information about the current tournament
- `/annuler` - Cancels the current tournament (admin only)

### Score Commands
- `/score <temps> [preuve]` - Submits a time for the current tournament
- `/messcores` - Shows the user's submitted times
- `/verifier <utilisateur> <action>` - Verifies or deletes a score (admin only)

### Administration Commands
- `/config [prefix] [role_admin]` - Configures the bot
- `/historique` - Displays tournament history

### Help Command
- `/aide` - Displays bot help information

## 🏗️ Project Structure

```
mk-timetrials-discord-bot/
├── main.py                 # Bot entry point
├── config.py               # Configuration and constants
├── .env                    # Environment variables (Discord token)
├── .env.example            # Example environment file
├── database/
│   ├── models.py           # Database schema definition
│   └── manager.py          # Database operations management
├── cogs/
│   ├── tournament.py       # Tournament management commands
│   ├── scores.py           # Score recording commands
│   └── admin.py            # Administration commands
├── utils/
│   ├── embeds.py           # Discord embeds creation
│   ├── logger.py           # Logging system
│   └── validators.py       # User input validation
├── data/
│   ├── courses.json        # MK8 Deluxe course data
│   └── tournaments.db      # SQLite database
└── requirements.txt        # Project dependencies
```

## 📝 Contributing

Contributions are welcome! To contribute:

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

Project Link: [https://github.com/ncarli/mk-timetrials-discord-bot](https://github.com/ncarli/mk-timetrials-discord-bot)