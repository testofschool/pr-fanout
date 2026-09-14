"""A fixed watchlist of widely recognised repositories.

The global numbers answer "is this happening"; the watchlist answers "is it
happening *here*", on projects a reader already has an opinion about. The list
is deliberately frozen in source (not discovered at runtime) so that every
published run covers the same repositories and a diff shows exactly when the
comparison set changed.

Selection rule, applied once: projects that (a) are household names in their
ecosystem, (b) accept outside pull requests, and (c) span more than one
language community, so the result cannot be an artefact of one toolchain.
"""
from __future__ import annotations

WATCHLIST: tuple[str, ...] = (
    # editors / platforms
    "microsoft/vscode",
    "neovim/neovim",
    "obsproject/obs-studio",
    "home-assistant/core",
    # web frameworks
    "facebook/react",
    "vercel/next.js",
    "vitejs/vite",
    "sveltejs/svelte",
    "angular/angular",
    "django/django",
    "rails/rails",
    # languages / runtimes
    "rust-lang/rust",
    "golang/go",
    "python/cpython",
    "nodejs/node",
    "denoland/deno",
    "microsoft/TypeScript",
    # infrastructure
    "kubernetes/kubernetes",
    "ansible/ansible",
    "grafana/grafana",
    "elastic/elasticsearch",
    "apache/airflow",
    "supabase/supabase",
    "n8n-io/n8n",
    # ML / AI
    "pytorch/pytorch",
    "tensorflow/tensorflow",
    "huggingface/transformers",
    "langchain-ai/langchain",
    "ollama/ollama",
    "openai/whisper",
    "scikit-learn/scikit-learn",
    "pandas-dev/pandas",
    "numpy/numpy",
    # systems / long-lived C projects
    "torvalds/linux",
    "curl/curl",
    "bitcoin/bitcoin",
    "godotengine/godot",
    "flutter/flutter",
)

_LOWER = {name.lower(): name for name in WATCHLIST}


def canonical(repo: str) -> str | None:
    """Return the watchlist spelling of ``repo``, or None if not watched.

    GH Archive preserves the repository name as it was at event time, so a
    rename or a case difference would silently drop a project from the table;
    matching case-insensitively is the cheap guard against that.
    """
    return _LOWER.get(repo.lower())
