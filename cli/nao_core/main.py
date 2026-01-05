from cyclopts import App

from nao_core.commands import chat, init

app = App()

app.command(chat)
app.command(init)

if __name__ == "__main__":
	app()
