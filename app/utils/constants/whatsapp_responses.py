class WAKEUP_MESSAGES:
    @staticmethod
    def new_user(name: str) -> str:
        return f"""
Hey {name}! 👋 I'm WAkeUp 📲 — your simple daily habit mirror on WhatsApp.

Just send me "log" each night to tell me how your day went.  
Then text "wake up" in the morning to get your personalized reflection.

No apps, no dashboards, no pressure — just 1 message a day.  
Ready to start?
"""

    @staticmethod
    def existing_user(name: str) -> str:
        return f"""
Welcome back, {name}! 🚀 Let's get back to it.

You know the drill: just send "log" tonight — and I'll turn your day into a quick, honest reflection by morning.

You're one message away from staying sharp. Let's keep the streak alive. 🔁
"""
