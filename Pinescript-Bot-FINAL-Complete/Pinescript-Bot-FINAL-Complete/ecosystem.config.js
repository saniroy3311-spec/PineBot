module.exports = {
  apps: [
    {
      name: "pinescript-bot",
      cwd: "/opt/pinescript-bot",
      script: "main.py",
      interpreter: "/opt/pinescript-bot/.venv/bin/python",
      env_file: "/opt/pinescript-bot/.env",
      autorestart: true,
      restart_delay: 5000
    }
  ]
};
