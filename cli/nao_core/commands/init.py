from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from nao_core.config import LLMConfig, LLMProvider, NaoConfig

console = Console()


class InitError(Exception):
    """Base exception for init command errors."""

    pass


class EmptyProjectNameError(InitError):
    """Raised when project name is empty."""

    def __init__(self):
        super().__init__("Project name cannot be empty.")


class ProjectExistsError(InitError):
    """Raised when project folder already exists."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        super().__init__(f"Folder '{project_name}' already exists.")


class EmptyApiKeyError(InitError):
    """Raised when API key is empty."""

    def __init__(self):
        super().__init__("API key cannot be empty.")


def setup_project_name() -> tuple[str, Path]:
    """Setup the project name."""
    project_name = Prompt.ask("[bold]Enter your project name[/bold]")

    if not project_name:
        raise EmptyProjectNameError()

    project_path = Path(project_name)

    if project_path.exists():
        raise ProjectExistsError(project_name)

    project_path.mkdir(parents=True)

    return project_name, project_path


def setup_llm() -> LLMConfig | None:
    """Setup the LLM configuration."""
    llm_config = None
    should_setup = Confirm.ask("\n[bold]Set up LLM configuration?[/bold]", default=True)

    if should_setup:
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
            raise EmptyApiKeyError()

        llm_config = LLMConfig(
            model=LLMProvider(llm_provider),
            api_key=api_key,
        )

    return llm_config


def init():
    """Initialize a new nao project.

    Creates a project folder with a nao_config.yaml configuration file.
    """
    console.print("\n[bold cyan]🚀 nao project initialization[/bold cyan]\n")

    try:
        project_name, project_path = setup_project_name()
        config = NaoConfig(
            project_name=project_name,
            llm=setup_llm(),
        )
        config.save(project_path)

        console.print()
        console.print(
            f"[bold green]✓[/bold green] Created project [cyan]{project_name}[/cyan]"
        )
        console.print(
            f"[bold green]✓[/bold green] Created [dim]{project_path / 'nao_config.yaml'}[/dim]"
        )
        console.print()
        console.print("[bold green]Done![/bold green] Your nao project is ready. 🎉")
    except InitError as e:
        console.print(f"[bold red]✗[/bold red] {e}")
