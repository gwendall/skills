# skills

My agent skills for Claude Code, Codex and compatible runtimes, grouped by category. One folder = one skill (`SKILL.md` + optional `references/` and `scripts/`). Each skill is self-contained: it ships every file it references, so it runs standalone. Modeled on [mattpocock/skills](https://github.com/mattpocock/skills).

## Skills

### Engineering

| Skill | What it does |
| --- | --- |
| [multi-agent-repo](skills/engineering/multi-agent-repo) | Audit or bootstrap a repo so many coding agents can work on it at the same time without stepping on each other. |
| [ci-cost-monorepo](skills/engineering/ci-cost-monorepo) | Diagnose and cut a runaway GitHub Actions bill in a monorepo. |
| [eas-monorepo-release](skills/engineering/eas-monorepo-release) | Ship an Expo app from a monorepo to TestFlight and the App Store with EAS, step by step. |

### Workstation

| Skill | What it does |
| --- | --- |
| [safe-disk-cleanup](skills/workstation/safe-disk-cleanup) | Reclaim disk space on a dev machine, with an explanation for every deletion and file-level dry-runs first. |
| [safe-memory-manager](skills/workstation/safe-memory-manager) | Diagnose RAM pressure on a dev Mac and find what can safely be stopped. |
| [claude-token-spend](skills/workstation/claude-token-spend) | Report Claude Code token consumption from your local session logs. |

### Crypto

| Skill | What it does |
| --- | --- |
| [wallet-analysis](skills/crypto/wallet-analysis) | Map the relationships of an EVM address: who funded it, who it transacts with, and which exchange the money came from. No API key. |

### Lifestyle

| Skill | What it does |
| --- | --- |
| [city-events](skills/lifestyle/city-events) | Events radar for Paris: art, tech, culture, gaming, food. |

### Writing

| Skill | What it does |
| --- | --- |
| [joke-writing](skills/writing/joke-writing) | Write jokes that are actually funny, tuned to the register you want. |

## Install

### Claude Code (plugin, recommended)

```
/plugin marketplace add gwendall/skills
/plugin install gwendall-skills@gwendall
```

Or from the shell:

```bash
claude plugin marketplace add gwendall/skills
claude plugin install gwendall-skills@gwendall
```

The plugin installs the whole set and updates when a new version is pushed.

### One skill only

Copy or symlink a single skill folder into your skills directory:

```bash
git clone https://github.com/gwendall/skills.git
ln -s "$PWD/skills/skills/workstation/safe-disk-cleanup" ~/.claude/skills/safe-disk-cleanup
```

For Codex, point the skill installer at a skill folder on GitHub, or symlink it into `~/.codex/skills/<skill>`.

### Local development (symlinks)

To edit skills live without reinstalling the plugin:

```bash
bin/sync.sh   # symlinks skills/<category>/<skill> -> ~/.claude/skills/<skill>
```

Idempotent; re-run it after a `git pull`. Skills are flattened by name, so skill names must stay unique across categories.

## Layout

```
.
├── .claude-plugin/
│   ├── marketplace.json   declares the "gwendall" marketplace
│   └── plugin.json        the "gwendall-skills" plugin and its skill list
├── skills/
│   ├── engineering/
│   │   ├── multi-agent-repo/
│   │   ├── ci-cost-monorepo/
│   │   └── eas-monorepo-release/
│   ├── workstation/
│   │   ├── safe-disk-cleanup/
│   │   ├── safe-memory-manager/
│   │   └── claude-token-spend/
│   ├── crypto/
│   │   └── wallet-analysis/
│   ├── lifestyle/
│   │   └── city-events/
│   └── writing/
│       └── joke-writing/
├── bin/
│   ├── sync.sh            symlinks every skill into ~/.claude/skills
│   └── build-index.py     regenerates index.json
├── tests/                 unit tests for the skills that ship scripts
└── index.json             generated manifest (skills, categories, files, URLs)
```

## Add a skill

1. Pick a category under `skills/`, or create a new one (a plain folder, lowercase, one word if possible).
2. Create `skills/<category>/<skill>/SKILL.md` with frontmatter `name` and `description`. The description is what triggers the skill, so make it say when to use it. Put requirements in the body so the skill stays portable across runtimes.
3. Add `./skills/<category>/<skill>` to the `skills` list in `.claude-plugin/plugin.json` and bump `version`.
4. Run `bin/build-index.py` (refresh `index.json`) and `bin/sync.sh` (local link).
5. If the skill ships scripts, add tests under `tests/` and run `python3 -m unittest discover -s tests`.

## Fetch by URL (optional)

Only useful if your agents load skills over HTTP instead of from disk. `index.json` lists each skill, its category and its files with absolute URLs (`GET .../index.json`, then `GET .../skills/<category>/<skill>/SKILL.md`). Regenerate it for another host with `bin/build-index.py --base-url <url>`.

## Language

Skills, docs and code comments are written in English: it is the working language of agents and keeps the skills shareable.

## License

[MIT](LICENSE)
