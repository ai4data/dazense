from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
	"""Supported LLM providers."""

	OPENAI = "openai"


class LLMConfig(BaseModel):
	"""LLM configuration."""

	model: LLMProvider = Field(description="The LLM provider to use")
	api_key: str = Field(description="The API key to use")

class NaoConfig(BaseModel):
	"""nao project configuration."""

	project_name: str = Field(description="The name of the nao project")
	llm: LLMConfig | None = Field(default=None, description="The LLM configuration")

	
	def save(self, path: Path) -> None:
		"""Save the configuration to a YAML file."""
		config_file = path / "nao_config.yaml"
		with config_file.open("w") as f:
			yaml.dump(
				self.model_dump(mode="json"),
				f,
				default_flow_style=False,
				sort_keys=False,
				allow_unicode=True,
			)

	@classmethod
	def load(cls, path: Path) -> "NaoConfig":
		"""Load the configuration from a YAML file."""
		config_file = path / "nao_config.yaml"
		with config_file.open() as f:
			data = yaml.safe_load(f)
		return cls.model_validate(data)

	@classmethod
	def try_load(cls, path: Path | None = None) -> "NaoConfig | None":
		"""Try to load config from path, returns None if not found or invalid.
		
		Args:
			path: Directory containing nao_config.yaml. Defaults to current directory.
		"""
		if path is None:
			path = Path.cwd()
		try:
			return cls.load(path)
		except (FileNotFoundError, ValueError, yaml.YAMLError):
			return None

	@classmethod
	def json_schema(cls) -> dict:
		"""Generate JSON schema for the configuration."""
		return cls.model_json_schema()