# Telegram Utility Bot

A feature-rich Telegram bot built using Python. It provides:

- Jokes on command  
- Daily motivational quotes  
- Personal note-taking  
- PDF summarization  
- Scheduled quotes 
- Hosted on [Railway](https://railway.app)

## Live Bot
You can interact with the bot here: [@PalAssistBot](https://t.me/PalAssistBot)

---

## Features

| Command            | Description                                  |
|--------------------|----------------------------------------------|
| `/start`           | Starts the bot and sends a welcome message   |
| `/wake`            | Pings the external API to wake it up         |
| `/joke`            | Sends a random joke                          |
| `/quote`           | Sends a motivational quote                   |
| `/note`            | Create or manage your personal notes         |
| `/summarize_pdf`   | Summarizes the PDF you upload                |

---

## Deployment

Deployed using **[Railway](https://railway.app)**

### 🛠 Build & Run Locally

1. **Clone this repo**:
    ```bash
    git clone https://github.com/guptakushal03/Telegram-Utility-Bot.git
    cd your-repo-name
    ```

2. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set environment variables**:
    - `TOKEN`

4. **Run the bot**:
    ```bash
    python server.py
    ```

---

## 📦 Requirements

Check `requirements.txt` for all dependencies.

---

## About

This bot was built to test and integrate multiple APIs with Telegram. It includes scheduled tasks, polling, and smart fallbacks to support free-tier limitations on hosting.

🧑‍💻 Built by [Kushal Ravindrakumar Gupta](https://github.com/guptakushal03)

👉 [View full source on GitHub](https://github.com/guptakushal03/Telegram-Utility-Bot)

---

## License

MIT License. Feel free to fork and customize!
