# Dependency environments

Choose one Chroma environment. Both Chroma distributions expose the same `chromadb` import, so do not install them together.

| Manifest | Purpose | Install from the repository root |
|---|---|---|
| `../requirements.txt` | Cloud/web development and CI; HTTP-only Chroma client | `python -m pip install -r requirements.txt` |
| `base.txt` | Shared quiz/development dependencies, included by the other manifests | Normally installed through one of the other manifests |
| `local.txt` | Full local Chroma and MiniLM; includes `base.txt` | `python -m pip install -r requirements/local.txt` |
| `../pyproject.toml` | Minimal production runtime dependencies used by Vercel | Installed by the deployment platform |

The full local environment also supports cloud connections. The cloud-only environment cannot start a local PersistentClient or download/run MiniLM. See [local retrieval](../docs/guides/chroma-local.md) and [cloud retrieval](../docs/guides/chroma-cloud.md).
