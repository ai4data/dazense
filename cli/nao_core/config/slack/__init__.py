from pydantic import BaseModel, Field


class SlackConfig(BaseModel):
    """Slack configuration."""

    bot_token: str = Field(description="The bot token to use")
    signing_secret: str = Field(description="The signing secret for verifying requests")
    post_message_url: str = Field(
        default="https://slack.com/api/chat.postMessage",
        description="The Slack API URL for posting messages",
    )
