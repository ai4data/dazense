from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from nao_core.config import LLMConfig, LLMProvider, NaoConfig

console = Console()


def init():
	"""Initialize a new nao project.

	Creates a project folder with a nao_config.yaml configuration file.
	"""
	console.print("\n[bold cyan]🚀 nao project initialization[/bold cyan]\n")

	project_name = Prompt.ask("[bold]Enter your project name[/bold]")

	if not project_name:
		console.print("[bold red]✗[/bold red] Project name cannot be empty.")
		return

	project_path = Path(project_name)

	if project_path.exists():
		console.print(
			f"[bold red]✗[/bold red] Folder [yellow]'{project_name}'[/yellow] already exists."
		)
		return

	# LLM Configuration
	llm_config = None
	setup_llm = Confirm.ask("\n[bold]Set up LLM configuration?[/bold]", default=True)

	if setup_llm:
		console.print("\n[bold cyan]LLM Configuration[/bold cyan]\n")

		provider_choices = [p.value for p in LLMProvider]
		llm_provider = Prompt.ask(
			"[bold]Select LLM provider[/bold]",
			choices=provider_choices,
			default=provider_choices[0],
		)

		api_key = Prompt.ask(
			f"[bold]Enter your {llm_provider.upper()} API key[/bold]",
			password=True,
		)

		if not api_key:
			console.print("[bold red]✗[/bold red] API key cannot be empty.")
			return

		llm_config = LLMConfig(
			model=LLMProvider(llm_provider),
			api_key=api_key,
		)

	project_path.mkdir(parents=True)

	config = NaoConfig(project_name=project_name, llm=llm_config)
	config.save(project_path)

	console.print()
	console.print(f"[bold green]✓[/bold green] Created project [cyan]{project_name}[/cyan]")
	console.print(
		f"[bold green]✓[/bold green] Created [dim]{project_path / 'nao_config.yaml'}[/dim]"
	)
	console.print()
	console.print("[bold green]Done![/bold green] Your nao project is ready. 🎉")

